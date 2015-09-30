/*
 * aplaymidi.c - play Standard MIDI Files to sequencer port(s)
 *
 * Copyright (c) 2004-2006 Clemens Ladisch <clemens@ladisch.de>
 *
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
 */

/* TODO: sequencer queue timer selection */

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <getopt.h>
#include <unistd.h>
#include <math.h>
#include <alsa/asoundlib.h>
#include "aconfig.h"
#include "version.h"

/*
 * 31.25 kbaud, one start bit, eight data bits, two stop bits.
 * (The MIDI spec says one stop bit, but every transmitter uses two, just to be
 * sure, so we better not exceed that to avoid overflowing the output buffer.)
 */
#define MIDI_BYTES_PER_SEC (31250 / (1 + 8 + 2))

/*
 * A MIDI event after being parsed/loaded from the file.
 * There could be made a case for using snd_seq_event_t instead.
 */
struct event {
	struct event *next;		/* linked list */

	unsigned char type;		/* SND_SEQ_EVENT_xxx */
	unsigned char port;		/* port index */
	unsigned int tick;
	union {
		unsigned char d[3];	/* channel and data bytes */
		int tempo;
		unsigned int length;	/* length of sysex data */
	} data;
	unsigned char sysex[0];
};

struct track {
	struct event *first_event;	/* list of all events in this track */
	int end_tick;			/* length of this track */

	struct event *current_event;	/* used while loading and playing */
        unsigned int volume[16];        /* Requested channel volumes (0-127) */
        unsigned int fade_volume[16];   /* Faded channel volumes (0-127) */
        unsigned int used[16];          /* Channel been used? */
	unsigned char port;		/* current port index */
};

/* --- church player stuff ----------------------------------------- */

#define RT__ABORT 'a'   /* Stop current song instantly */
#define RT__FADE  'f'   /* Fade out and then stop current song */
#define RT__EMPTY 'e'   /* Remove any remaing songs from the playlist */
#define RT__STOP  's'   /* Let each note finish then stop current song */
#define RT__TERM  't'   /* Terminate player */
#define RT__PLAY  'p'   /* Queue song on playlist */
#define RT__PROG0 'i'   /* Instrument (program change for channel 0) */
#define RT__TRANS 'r'   /* Change transposition */
#define RT__TEMPO 'm'   /* Change tempo */
#define RT__NULL  ' '

#define RT__PLAYING 'p' /* A song is being played */
#define RT__STOPPED 's' /* No song is being played */
#define RT__ENDING  'e' /* Player is about to terminate */

#define RT__FIFO_RD "/tmp/churchplayerfifo_rd"
#define RT__FIFO_WR "/tmp/churchplayerfifo_wr"
#define RT__NFADE 300
#define RT__FADE_STEP 20000.0
#define RT__MAX_VOLUME 127
#define RT__PI 3.1415926
#define RT__MAX_SONG 50
#define RT__SONG_LEN 150
#define RT__NVAL 3

#define RT__BAD_FIFO_RD 0
#define RT__BAD_FIFO_WR 1
#define RT__SONG_TOO_LONG 2
#define RT__SONG_OOB_P 3
#define RT__SONG_OOB_N 4

static const char *rt_message[] = {
   "churchplayer: Failed to read from reader FIFO",
   "churchplayer: Failed to write to writer FIFO",
   "churchplayer: Song data too long",
   "churchplayer: Playlist population went too high",
   "churchplayer: Playlist population went negative"
};

static char rt_playlist[ RT__MAX_SONG*RT__SONG_LEN ];
static int rt_song_r = 0;
static int rt_song_w = 0;
static int rt_nsong = 0;
static int rt_terminate = 0;
static int rt_fdr = -1;
static int rt_fdw = -1;
static int rt_mspqn = 0;
static int rt_mspqn_req = 0;
static int rt_ppqn = 0;
static int rt_verbose = 0;
static char rt_inst = -1;
static char rt_tran = 0;
static float rt_tempofactor = 1.0;

static char rt_cmd( void );
static char rt_get_code( void );
static char rt_get_code_blocking( void );
static int rt_create_fifo_rd( void );
static int rt_create_fifo_wr( void );
static int rt_pop_file( void );
static void rt_change_volume( unsigned int tick, float gain, int used_only );
static void rt_change_prog0( unsigned int tick, char prog0 );
static void rt_create_fadeout_profile( int nfade, float *fade_gains );
static void rt_destroy_fifo_rd( void );
static void rt_destroy_fifo_wr( void );
static void rt_error( int error );
static void rt_send_event( snd_seq_event_t *ev );
static void rt_send_reply( char code, const char *text );
static void rt_all_notes_off( snd_seq_event_t *ev );
static void rt_change_tempo( snd_seq_event_t *ev, struct event* event );

/* ------------------------------------------------------ */

static snd_seq_t *seq;
static int client;
static int port_count;
static snd_seq_addr_t *ports;
static int queue;
static int end_delay = 2;
static const char *file_name;
static FILE *file;
static int file_offset;		/* current offset in input file */
static int num_tracks;
static struct track *tracks;
static int smpte_timing;

/* prints an error message to stderr */
static void errormsg(const char *msg, ...)
{
	va_list ap;

	va_start(ap, msg);
	vfprintf(stderr, msg, ap);
	va_end(ap);
	fputc('\n', stderr);
}

/* prints an error message to stderr, and dies */
static void fatal(const char *msg, ...)
{
	va_list ap;

	va_start(ap, msg);
	vfprintf(stderr, msg, ap);
	va_end(ap);
	fputc('\n', stderr);
	exit(EXIT_FAILURE);
}

/* memory allocation error handling */
static void check_mem(void *p)
{
	if (!p)
		fatal("Out of memory");
}

/* error handling for ALSA functions */
static void check_snd(const char *operation, int err)
{
	if (err < 0)
		fatal("Cannot %s - %s", operation, snd_strerror(err));
}

static void init_seq(void)
{
	int err;

	/* open sequencer */
	err = snd_seq_open(&seq, "default", SND_SEQ_OPEN_DUPLEX, 0);
	check_snd("open sequencer", err);

	/* set our name (otherwise it's "Client-xxx") */
	err = snd_seq_set_client_name(seq, "aplaymidi");
	check_snd("set client name", err);

	/* find out who we actually are */
	client = snd_seq_client_id(seq);
	check_snd("get client id", client);
}

/* parses one or more port addresses from the string */
static void parse_ports(const char *arg)
{
	char *buf, *s, *port_name;
	int err;

	/* make a copy of the string because we're going to modify it */
	buf = strdup(arg);
	check_mem(buf);

	for (port_name = s = buf; s; port_name = s + 1) {
		/* Assume that ports are separated by commas.  We don't use
		 * spaces because those are valid in client names. */
		s = strchr(port_name, ',');
		if (s)
			*s = '\0';

		++port_count;
		ports = realloc(ports, port_count * sizeof(snd_seq_addr_t));
		check_mem(ports);

		err = snd_seq_parse_address(seq, &ports[port_count - 1], port_name);
		if (err < 0)
			fatal("Invalid port %s - %s", port_name, snd_strerror(err));
	}

	free(buf);
}

static void create_source_port(void)
{
	snd_seq_port_info_t *pinfo;
	int err;

	snd_seq_port_info_alloca(&pinfo);

	/* the first created port is 0 anyway, but let's make sure ... */
	snd_seq_port_info_set_port(pinfo, 0);
	snd_seq_port_info_set_port_specified(pinfo, 1);

	snd_seq_port_info_set_name(pinfo, "aplaymidi");

	snd_seq_port_info_set_capability(pinfo, 0); /* sic */
	snd_seq_port_info_set_type(pinfo,
				   SND_SEQ_PORT_TYPE_MIDI_GENERIC |
				   SND_SEQ_PORT_TYPE_APPLICATION);

	err = snd_seq_create_port(seq, pinfo);
	check_snd("create port", err);
}

static void create_queue(void)
{
	queue = snd_seq_alloc_named_queue(seq, "aplaymidi");
	check_snd("create queue", queue);
	/* the queue is now locked, which is just fine */
}

static void free_queue(void)
{
        int err = snd_seq_free_queue( seq, queue );
	check_snd("free queue", err );
}

static void connect_ports(void)
{
	int i, err;

	/*
	 * We send MIDI events with explicit destination addresses, so we don't
	 * need any connections to the playback ports.  But we connect to those
	 * anyway to force any underlying RawMIDI ports to remain open while
	 * we're playing - otherwise, ALSA would reset the port after every
	 * event.
	 */
	for (i = 0; i < port_count; ++i) {
		err = snd_seq_connect_to(seq, 0, ports[i].client, ports[i].port);
		if (err < 0)
			fatal("Cannot connect to port %d:%d - %s",
			      ports[i].client, ports[i].port, snd_strerror(err));
	}
}

static int read_byte(void)
{
	++file_offset;
	return getc(file);
}

/* reads a little-endian 32-bit integer */
static int read_32_le(void)
{
	int value;
	value = read_byte();
	value |= read_byte() << 8;
	value |= read_byte() << 16;
	value |= read_byte() << 24;
	return !feof(file) ? value : -1;
}

/* reads a 4-character identifier */
static int read_id(void)
{
	return read_32_le();
}
#define MAKE_ID(c1, c2, c3, c4) ((c1) | ((c2) << 8) | ((c3) << 16) | ((c4) << 24))

/* reads a fixed-size big-endian number */
static int read_int(int bytes)
{
	int c, value = 0;

	do {
		c = read_byte();
		if (c == EOF)
			return -1;
		value = (value << 8) | c;
	} while (--bytes);
	return value;
}

/* reads a variable-length number */
static int read_var(void)
{
	int value, c;

	c = read_byte();
	value = c & 0x7f;
	if (c & 0x80) {
		c = read_byte();
		value = (value << 7) | (c & 0x7f);
		if (c & 0x80) {
			c = read_byte();
			value = (value << 7) | (c & 0x7f);
			if (c & 0x80) {
				c = read_byte();
				value = (value << 7) | c;
				if (c & 0x80)
					return -1;
			}
		}
	}
	return !feof(file) ? value : -1;
}

/* allocates a new event */
static struct event *new_event(struct track *track, int sysex_length)
{
	struct event *event;

	event = malloc(sizeof(struct event) + sysex_length);
	check_mem(event);

	event->next = NULL;

	/* append at the end of the track's linked list */
	if (track->current_event)
		track->current_event->next = event;
	else
		track->first_event = event;
	track->current_event = event;

	return event;
}

static void skip(int bytes)
{
	while (bytes > 0)
		read_byte(), --bytes;
}

/* reads one complete track from the file */
static int read_track(struct track *track, int track_end, int itrack )
{
        int i;
	int tick = 0;
	unsigned char last_cmd = 0;
	unsigned char port = 0;

        /* initialise track volume to max (127) for each channel. */
        for( i = 0; i < 16; i++ ) {
           track->volume[ i ] = RT__MAX_VOLUME;
           track->fade_volume[ i ] = -1;
           track->used[ i ] = 0;
        }

	/* the current file position is after the track ID and length */
	while (file_offset < track_end) {
		unsigned char cmd;
		struct event *event;
		int delta_ticks, len, c;

		delta_ticks = read_var();
		if (delta_ticks < 0)
			break;
		tick += delta_ticks;

		c = read_byte();
		if (c < 0)
			break;

		if (c & 0x80) {
			/* have command */
			cmd = c;
			if (cmd < 0xf0)
				last_cmd = cmd;
		} else {
			/* running status */
			ungetc(c, file);
			file_offset--;
			cmd = last_cmd;
			if (!cmd)
				goto _error;
		}

		switch (cmd >> 4) {
			/* maps SMF events to ALSA sequencer events */
			static const unsigned char cmd_type[] = {
				[0x8] = SND_SEQ_EVENT_NOTEOFF,
				[0x9] = SND_SEQ_EVENT_NOTEON,
				[0xa] = SND_SEQ_EVENT_KEYPRESS,
				[0xb] = SND_SEQ_EVENT_CONTROLLER,
				[0xc] = SND_SEQ_EVENT_PGMCHANGE,
				[0xd] = SND_SEQ_EVENT_CHANPRESS,
				[0xe] = SND_SEQ_EVENT_PITCHBEND
			};

		case 0x8: /* channel msg with 2 parameter bytes */
		case 0x9:
		case 0xa:
		case 0xb:
		case 0xe:
			event = new_event(track, 0);
			event->type = cmd_type[cmd >> 4];
			event->port = port;
			event->tick = tick;
			event->data.d[0] = cmd & 0x0f;
			event->data.d[1] = read_byte() & 0x7f;
			event->data.d[2] = read_byte() & 0x7f;

			break;

		case 0xc: /* channel msg with 1 parameter byte */
		case 0xd:
			event = new_event(track, 0);
			event->type = cmd_type[cmd >> 4];
			event->port = port;
			event->tick = tick;
			event->data.d[0] = cmd & 0x0f;
			event->data.d[1] = read_byte() & 0x7f;

                        if( event->type == SND_SEQ_EVENT_PGMCHANGE &&
                            rt_inst > -1 ) {
                           event->data.d[1] = rt_inst & 0x7f;
                        }

/*
                        if( rt_verbose ) {
                           if( event->type == SND_SEQ_EVENT_PGMCHANGE ) {
                              printf( "aplaymidi: PgmChg: T:%d C:%d D:%d \n", itrack,
                                      event->data.d[0], event->data.d[1] );
                           }
                        }
*/

			break;

		case 0xf:
			switch (cmd) {
			case 0xf0: /* sysex */
			case 0xf7: /* continued sysex, or escaped commands */
				len = read_var();
				if (len < 0)
					goto _error;
				if (cmd == 0xf0)
					++len;
				event = new_event(track, len);
				event->type = SND_SEQ_EVENT_SYSEX;
				event->port = port;
				event->tick = tick;
				event->data.length = len;
				if (cmd == 0xf0) {
					event->sysex[0] = 0xf0;
					c = 1;
				} else {
					c = 0;
				}
				for (; c < len; ++c)
					event->sysex[c] = read_byte();
				break;

			case 0xff: /* meta event */
				c = read_byte();
				len = read_var();
				if (len < 0)
					goto _error;

				switch (c) {
				case 0x21: /* port number */
					if (len < 1)
						goto _error;
					port = read_byte() % port_count;
					skip(len - 1);
					break;

				case 0x2f: /* end of track */
					track->end_tick = tick;
					skip(track_end - file_offset);
					return 1;

				case 0x51: /* tempo */
					if (len < 3)
						goto _error;
					if (smpte_timing) {
						/* SMPTE timing doesn't change */
						skip(len);
					} else {
						event = new_event(track, 0);
						event->type = SND_SEQ_EVENT_TEMPO;
						event->port = port;
						event->tick = tick;
						event->data.tempo = read_byte() << 16;
						event->data.tempo |= read_byte() << 8;
						event->data.tempo |= read_byte();
						skip(len - 3);
					}
					break;

				default: /* ignore all other meta events */
					skip(len);
					break;
				}
				break;

			default: /* invalid Fx command */
				goto _error;
			}
			break;

		default: /* cannot happen */
			goto _error;
		}
	}
_error:
	errormsg("%s: invalid MIDI data (offset %#x)", file_name, file_offset);
	return 0;
}

/* reads an entire MIDI file */
static int read_smf(void)
{
	int header_len, type, time_division, i, err;
	snd_seq_queue_tempo_t *queue_tempo;

	/* the curren position is immediately after the "MThd" id */
	header_len = read_int(4);
	if (header_len < 6) {
invalid_format:
		errormsg("%s: invalid file format", file_name);
		return 0;
	}

	type = read_int(2);
	if (type != 0 && type != 1) {
		errormsg("%s: type %d format is not supported", file_name, type);
		return 0;
	}

	num_tracks = read_int(2);
	if (num_tracks < 1 || num_tracks > 1000) {
		errormsg("%s: invalid number of tracks (%d)", file_name, num_tracks);
		num_tracks = 0;
		return 0;
	}
	tracks = calloc(num_tracks, sizeof(struct track));
	if (!tracks) {
		errormsg("out of memory");
		num_tracks = 0;
		return 0;
	}

	time_division = read_int(2);
	if (time_division < 0)
		goto invalid_format;

	/* interpret and set tempo */
	snd_seq_queue_tempo_alloca(&queue_tempo);
	smpte_timing = !!(time_division & 0x8000);
	if (!smpte_timing) {
		/* time_division is ticks per quarter */
                rt_mspqn_req = rt_mspqn = 500000;
                rt_ppqn = time_division;
		snd_seq_queue_tempo_set_tempo(queue_tempo, 500000); /* default: 120 bpm */
		snd_seq_queue_tempo_set_ppq(queue_tempo, time_division);
	} else {
		/* upper byte is negative frames per second */
		i = 0x80 - ((time_division >> 8) & 0x7f);
		/* lower byte is ticks per frame */
		time_division &= 0xff;
		/* now pretend that we have quarter-note based timing */
		switch (i) {
		case 24:
                        rt_mspqn_req = rt_mspqn = 500000;
                        rt_ppqn = 12 * time_division;
			snd_seq_queue_tempo_set_tempo(queue_tempo, 500000);
			snd_seq_queue_tempo_set_ppq(queue_tempo, rt_ppqn );
			break;
		case 25:
                        rt_mspqn_req = rt_mspqn = 400000;
                        rt_ppqn = 10 * time_division;
			snd_seq_queue_tempo_set_tempo(queue_tempo, 400000);
			snd_seq_queue_tempo_set_ppq(queue_tempo, rt_ppqn );
			break;
		case 29: /* 30 drop-frame */
                        rt_mspqn_req = rt_mspqn = 100000000;
                        rt_ppqn = 2997 * time_division;
			snd_seq_queue_tempo_set_tempo(queue_tempo, 100000000);
			snd_seq_queue_tempo_set_ppq(queue_tempo, rt_ppqn );
			break;
		case 30:
                        rt_mspqn_req = rt_mspqn = 500000;
                        rt_ppqn = 15 * time_division;
			snd_seq_queue_tempo_set_tempo(queue_tempo, 500000);
			snd_seq_queue_tempo_set_ppq(queue_tempo, rt_ppqn );
			break;
		default:
			errormsg("%s: invalid number of SMPTE frames per second (%d)",
				 file_name, i);
			return 0;
		}
	}
	err = snd_seq_set_queue_tempo(seq, queue, queue_tempo);
	if (err < 0) {
		errormsg("Cannot set queue tempo (%u/%i)",
			 snd_seq_queue_tempo_get_tempo(queue_tempo),
			 snd_seq_queue_tempo_get_ppq(queue_tempo));
		return 0;
	}

	/* read tracks */
	for (i = 0; i < num_tracks; ++i) {
		int len;

		/* search for MTrk chunk */
		for (;;) {
			int id = read_id();
			len = read_int(4);
			if (feof(file)) {
				errormsg("%s: unexpected end of file", file_name);
				return 0;
			}
			if (len < 0 || len >= 0x10000000) {
				errormsg("%s: invalid chunk length %d", file_name, len);
				return 0;
			}
			if (id == MAKE_ID('M', 'T', 'r', 'k'))
				break;
			skip(len);
		}
		if (!read_track(&tracks[i], file_offset + len, i))
			return 0;
	}
	return 1;
}

static int read_riff(void)
{
	/* skip file length */
	read_byte();
	read_byte();
	read_byte();
	read_byte();

	/* check file type ("RMID" = RIFF MIDI) */
	if (read_id() != MAKE_ID('R', 'M', 'I', 'D')) {
invalid_format:
		errormsg("%s: invalid file format", file_name);
		return 0;
	}
	/* search for "data" chunk */
	for (;;) {
		int id = read_id();
		int len = read_32_le();
		if (feof(file)) {
data_not_found:
			errormsg("%s: data chunk not found", file_name);
			return 0;
		}
		if (id == MAKE_ID('d', 'a', 't', 'a'))
			break;
		if (len < 0)
			goto data_not_found;
		skip((len + 1) & ~1);
	}
	/* the "data" chunk must contain data in SMF format */
	if (read_id() != MAKE_ID('M', 'T', 'h', 'd'))
		goto invalid_format;
	return read_smf();
}

static void cleanup_file_data(void)
{
	int i;
	struct event *event;

	for (i = 0; i < num_tracks; ++i) {
		event = tracks[i].first_event;
		while (event) {
			struct event *next = event->next;
			free(event);
			event = next;
		}
	}
	num_tracks = 0;
	free(tracks);
	tracks = NULL;
}

static void handle_big_sysex(snd_seq_event_t *ev)
{
	unsigned int length;
	ssize_t event_size;
	int err;
	length = ev->data.ext.len;
	if (length > MIDI_BYTES_PER_SEC)
		ev->data.ext.len = MIDI_BYTES_PER_SEC;
	event_size = snd_seq_event_length(ev);
	if (event_size + 1 > snd_seq_get_output_buffer_size(seq)) {
		err = snd_seq_drain_output(seq);
		check_snd("drain output", err);
		err = snd_seq_set_output_buffer_size(seq, event_size + 1);
		check_snd("set output buffer size", err);
	}
	while (length > MIDI_BYTES_PER_SEC) {
		err = snd_seq_event_output(seq, ev);
		check_snd("output event", err);
		err = snd_seq_drain_output(seq);
		check_snd("drain output", err);
		err = snd_seq_sync_output_queue(seq);
		check_snd("sync output", err);
		if (sleep(1))
			fatal("aborted");
		ev->data.ext.ptr += MIDI_BYTES_PER_SEC;
		length -= MIDI_BYTES_PER_SEC;
	}
	ev->data.ext.len = length;
}

static void play_midi(void)
{
	snd_seq_event_t ev;
	int ignore, i, j, max_tick, err;
        char rt_code = RT__NULL;
        float fade_gains[ RT__NFADE ];
        int next_fade_tick = -1;
        int ifade = -1;
        int first_event = 1;
        int max_fade;
        int delay = 1;

	/* calculate length of the entire file, and reset track info */
	max_tick = -1;
	for (i = 0; i < num_tracks; ++i) {
		if (tracks[i].end_tick > max_tick)
			max_tick = tracks[i].end_tick;
        }

	/* initialize current position in each track */
	for (i = 0; i < num_tracks; ++i){
	   tracks[i].current_event = tracks[i].first_event;
           tracks[i].port = 0;
        }

	/* common settings for all our events */
	snd_seq_ev_clear(&ev);
	ev.queue = queue;
	ev.source.port = 0;
	ev.flags = SND_SEQ_TIME_STAMP_TICK;

	err = snd_seq_start_queue(seq, queue, NULL);
	check_snd("start queue", err);

	/* The queue won't be started until the START_QUEUE event is
	 * actually drained to the kernel, which is exactly what we want. */
        first_event = 1;
        for (;;) {
		struct event* event = NULL;
		struct track* event_track = NULL;
		int i, min_tick = max_tick + 1;

		/* search next event */
		for (i = 0; i < num_tracks; ++i) {
			struct track *track = &tracks[i];
			struct event *e2 = track->current_event;
			if (e2 && e2->tick < min_tick) {
				min_tick = e2->tick;
				event = e2;
				event_track = track;
			}
		}
		if (!event)
			break; /* end of song reached */

		/* advance pointer to next event */
		event_track->current_event = event->next;

                /* See if any control signals have been sent to this midi
                   player. But do not do this if we are currently already
                   processing a previosu control signal. */
                if( rt_code == RT__NULL ) rt_code = rt_cmd();

                /* Change instrument for channel 0. */
                if( rt_code == RT__PROG0 ) {
                   rt_change_prog0( event->tick, rt_inst );
                   rt_code = RT__NULL;

                /* If the transposition (rt_tran) was changed, send an
                   all notes off signal so that we do not mix "note on"s
                   and "note off"s with different transpositions. */
                } else if( rt_code == RT__TRANS ) {
                   rt_all_notes_off( &ev );
                   rt_code = RT__NULL;

                /* If the tempo factor has been changed, send a tempo
                   change to the synth. */
                } else if( rt_code == RT__TEMPO ) {
                   rt_change_tempo( &ev, event );
                   rt_code = RT__NULL;

                /* Stop after all the currently sounding notes have
                   finished. */
                } else if( ( rt_code == RT__STOP || rt_code == RT__FADE )
                           && ifade >= 0 && ifade >= max_fade ) {
                   rt_code = RT__ABORT;
                   delay = 0;

                /* Stop now, by sending "all notes off" to all channels of
                   each track. */
                } else if( rt_code == RT__ABORT ) {
                   ev.time.tick += 1;
                   rt_all_notes_off( &ev );
                   break;

                } else if( (rt_code == RT__STOP || rt_code == RT__FADE)
                           && ifade == -1 ) {
                   rt_create_fadeout_profile( RT__NFADE, fade_gains );
                   next_fade_tick = event->tick - 1;
                   ifade = 0;
                   max_fade = (rt_code == RT__FADE) ? RT__NFADE : RT__NFADE/7;

                } else if( rt_code != RT__FADE && rt_code != RT__STOP &&
                           rt_code != RT__ABORT ) {
                   rt_code =RT__NULL;

                }

                /* Ensure full volume to start. */
                if( first_event ) {
                   rt_change_volume( event->tick, 1.0, 0 );
                   first_event = 0;
                }

		/* output the event */
                ignore = 0;
		ev.type = event->type;
		ev.time.tick = event->tick;
		ev.dest = ports[event->port];
                event_track->port = event->port;

                if( rt_code == RT__FADE || rt_code == RT__STOP ) {
                   int tickgap = RT__FADE_STEP*((double)rt_ppqn/(double)rt_mspqn);

                   while( next_fade_tick < event->tick &&
                          ifade < RT__NFADE ) {
                      if( rt_code == RT__FADE ) rt_change_volume( next_fade_tick, fade_gains[ ifade ], 1 );
                      ifade++;
                      next_fade_tick += tickgap;
                   }
                }

		switch (ev.type) {
		case SND_SEQ_EVENT_NOTEON:
		case SND_SEQ_EVENT_NOTEOFF:
		case SND_SEQ_EVENT_KEYPRESS:
                        if( ev.type == SND_SEQ_EVENT_NOTEON &&
                            (rt_code == RT__STOP || rt_code == RT__ABORT) ) ignore = 1;
			snd_seq_ev_set_fixed(&ev);
			ev.data.note.channel = event->data.d[0];
			ev.data.note.note = event->data.d[1] + rt_tran;
			ev.data.note.velocity = event->data.d[2];
                        event_track->used[ ev.data.note.channel ] = 1;

			break;
		case SND_SEQ_EVENT_CONTROLLER:
			snd_seq_ev_set_fixed(&ev);
			ev.data.control.channel = event->data.d[0];
			ev.data.control.param = event->data.d[1];
			ev.data.control.value = event->data.d[2];

                        /* Record any changes to channel volume. */
                        if( event->data.d[1]  == 7 ) {
                           event_track->volume[ event->data.d[0] ] = event->data.d[2];
                        }

			break;
		case SND_SEQ_EVENT_PGMCHANGE:
		case SND_SEQ_EVENT_CHANPRESS:
			snd_seq_ev_set_fixed(&ev);
			ev.data.control.channel = event->data.d[0];
			ev.data.control.value = event->data.d[1];
			break;
		case SND_SEQ_EVENT_PITCHBEND:
			snd_seq_ev_set_fixed(&ev);
			ev.data.control.channel = event->data.d[0];
			ev.data.control.value =
				((event->data.d[1]) |
				 ((event->data.d[2]) << 7)) - 0x2000;
			break;
		case SND_SEQ_EVENT_SYSEX:
			snd_seq_ev_set_variable(&ev, event->data.length,
						event->sysex);
			handle_big_sysex(&ev);
			break;
		case SND_SEQ_EVENT_TEMPO:
			snd_seq_ev_set_fixed(&ev);
			ev.dest.client = SND_SEQ_CLIENT_SYSTEM;
			ev.dest.port = SND_SEQ_PORT_SYSTEM_TIMER;
			ev.data.queue.queue = queue;
                        rt_mspqn_req = event->data.tempo;
                        rt_mspqn = (int) (rt_mspqn_req/rt_tempofactor);
			ev.data.queue.param.value = rt_mspqn;
			break;
		default:
			fatal("Invalid event type %d!", ev.type);
		}


                /* Do not send note-on events after an abort has been
                   requested. */
                if( !ignore ) rt_send_event( &ev );
	}

	/* schedule queue stop at end of song */
	snd_seq_ev_set_fixed(&ev);
	ev.type = SND_SEQ_EVENT_STOP;
	ev.time.tick = max_tick;
	ev.dest.client = SND_SEQ_CLIENT_SYSTEM;
	ev.dest.port = SND_SEQ_PORT_SYSTEM_TIMER;
	ev.data.queue.queue = queue;
	err = snd_seq_event_output(seq, &ev);
	check_snd("output event", err);

	/* make sure that the sequencer sees all our events */
	err = snd_seq_drain_output(seq);
	check_snd("drain output", err);

	/*
	 * There are three possibilities how to wait until all events have
	 * been played:
	 * 1) send an event back to us (like pmidi does), and wait for it;
	 * 2) wait for the EVENT_STOP notification for our queue which is sent
	 *    by the system timer port (this would require a subscription);
	 * 3) wait until the output pool is empty.
	 * The last is the simplest.
	 */
        if( rt_code != RT__STOP && rt_code != RT__ABORT ) {
           err = snd_seq_sync_output_queue(seq);
	   check_snd("sync output", err);
        }

	/* give the last notes time to die away */
	if (delay && end_delay > 0)
		sleep(end_delay);
}

static void rt_send_event( snd_seq_event_t *ev ){
   int err;

   /* Add the event to the buffer. This blocks when the output
      pool has been filled */
   err = snd_seq_event_output(seq, ev);
   check_snd("output event", err);

   /* For RT control, wait until the event has been processed
      before sending the next event to the buffer. This means
      this function returns as soon as the supplied event has
      been processed. */
   if( rt_fdr != -1 ) {
      err = snd_seq_drain_output(seq);
      check_snd("drain output", err);
      snd_seq_sync_output_queue(seq);
      check_snd("sync output queue", err);
   }
}



static void play_file(void)
{
	int ok;

	if (!strcmp(file_name, "-"))
		file = stdin;
	else
		file = fopen(file_name, "rb");
	if (!file) {
		errormsg("Cannot open %s - %s", file_name, strerror(errno));
		return;
	}

        rt_send_reply( RT__PLAYING, file_name );

	file_offset = 0;
	ok = 0;

	switch (read_id()) {
	case MAKE_ID('M', 'T', 'h', 'd'):
		ok = read_smf();
		break;
	case MAKE_ID('R', 'I', 'F', 'F'):
		ok = read_riff();
		break;
	default:
		errormsg("%s is not a Standard MIDI File", file_name);
		break;
	}

	if (file != stdin)
		fclose(file);

	if (ok)
		play_midi();

	cleanup_file_data();
        rt_send_reply( RT__STOPPED, NULL );
}

static void list_ports(void)
{
	snd_seq_client_info_t *cinfo;
	snd_seq_port_info_t *pinfo;

	snd_seq_client_info_alloca(&cinfo);
	snd_seq_port_info_alloca(&pinfo);

	puts(" Port    Client name                      Port name");

	snd_seq_client_info_set_client(cinfo, -1);
	while (snd_seq_query_next_client(seq, cinfo) >= 0) {
		int client = snd_seq_client_info_get_client(cinfo);

		snd_seq_port_info_set_client(pinfo, client);
		snd_seq_port_info_set_port(pinfo, -1);
		while (snd_seq_query_next_port(seq, pinfo) >= 0) {
			/* port must understand MIDI messages */
			if (!(snd_seq_port_info_get_type(pinfo)
			      & SND_SEQ_PORT_TYPE_MIDI_GENERIC))
				continue;
			/* we need both WRITE and SUBS_WRITE */
			if ((snd_seq_port_info_get_capability(pinfo)
			     & (SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE))
			    != (SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_WRITE))
				continue;
			printf("%3d:%-3d  %-32.32s %s\n",
			       snd_seq_port_info_get_client(pinfo),
			       snd_seq_port_info_get_port(pinfo),
			       snd_seq_client_info_get_name(cinfo),
			       snd_seq_port_info_get_name(pinfo));
		}
	}
}

static void usage(const char *argv0)
{
	printf(
		"Usage: %s -p client:port[,...] [-d delay] midifile ...\n"
		"-h, --help                  this help\n"
		"-V, --version               print current version\n"
		"-r, --rt_listen             listen for churchplayer control\n"
		"-y, --rt_reply              reply to churchplayer\n"
		"-v, --verbose               report instruments etc\n"
		"-l, --list                  list all possible output ports\n"
		"-p, --port=client:port,...  set port(s) to play to\n"
		"-d, --delay=seconds         delay after song ends\n",
		argv0);
}

static void version(void)
{
	puts("aplaymidi version " SND_UTIL_VERSION_STR);
}

int main(int argc, char *argv[])
{
	static const char short_options[] = "hVlp:d:ryv";
	static const struct option long_options[] = {
		{"help", 0, NULL, 'h'},
		{"version", 0, NULL, 'V'},
		{"list", 0, NULL, 'l'},
		{"port", 1, NULL, 'p'},
		{"delay", 1, NULL, 'd'},
		{"rt_listen", 0, NULL, 'r'},
		{"rt_reply", 0, NULL, 'y'},
		{"verbose", 0, NULL, 'v'},
		{}
	};
	int c;
	int do_list = 0;
        int rt_listen = 0;
        int rt_reply = 0;

	init_seq();

	while ((c = getopt_long(argc, argv, short_options,
				long_options, NULL)) != -1) {
		switch (c) {
		case 'h':
			usage(argv[0]);
			return 0;
		case 'V':
			version();
			return 0;
		case 'l':
			do_list = 1;
			break;
		case 'p':
			parse_ports(optarg);
			break;
		case 'd':
			end_delay = atoi(optarg);
			break;
		case 'r':
			rt_listen = 1;
			break;
		case 'y':
			rt_reply = 1;
			break;
		case 'v':
			rt_verbose = 1;
			break;
		default:
			usage(argv[0]);
			return 1;
		}
	}

        if( rt_listen && !rt_create_fifo_rd() ) return 1;
        if( rt_reply && !rt_create_fifo_wr() ) return 1;

	if (do_list) {
		list_ports();
	} else {
		if (port_count < 1) {
			/* use env var for compatibility with pmidi */
			const char *ports_str = getenv("ALSA_OUTPUT_PORTS");
			if (ports_str)
				parse_ports(ports_str);
			if (port_count < 1) {
				errormsg("Please specify at least one port with --port.");
				return 1;
			}
		}

		create_source_port();
		connect_ports();

                if( rt_listen ) {
   	           if (optind >= argc) {
                      char cmd;
                      while( !rt_terminate ) {
                         if( rt_pop_file() ) {
                            create_queue();
                            play_file();
                            free_queue();
                         } else {
                            cmd = rt_cmd();
                            if( cmd == RT__NULL ) sleep( 1 );
                         }
                      }
                      rt_send_reply( RT__ENDING, NULL );

                   } else {
                      create_queue();
         	      file_name = argv[optind];
         	      play_file();
                   }

                } else {
   	           if (optind >= argc) {
   			errormsg("Please specify a file to play.");
   			return 1;
                   }

                   create_queue();
         	   for (; optind < argc; ++optind) {
         	      file_name = argv[optind];
         	      play_file();
         	   }
                }


	}
	snd_seq_close(seq);
        if( rt_listen ) rt_destroy_fifo_rd();
        if( rt_reply ) rt_destroy_fifo_wr();
	return 0;
}



static int rt_create_fifo_rd( void ){
    int istat = 1;
    mkfifo( RT__FIFO_RD, 0666 );
    rt_fdr = open( RT__FIFO_RD, O_RDONLY | O_NONBLOCK );
    if( rt_fdr == -1 ) {
       perror( "Failed to create churchplayer reader FIFO" );
       istat = 0;
    }
    return istat;
}


static int rt_create_fifo_wr( void ){
    int istat = 1;
    if( mkfifo( RT__FIFO_WR, 0666 ) ) {
       perror( "Failed to create churchplayer writer FIFO" );
       istat = 0;
    } else {
       rt_fdw = open( RT__FIFO_WR, O_WRONLY );
       if( rt_fdw == -1 ) {
          perror( "Failed to open churchplayer writer FIFO" );
          istat = 0;
       }
    }
    return istat;
}

static void rt_destroy_fifo_rd( void ){
    if( rt_fdr != -1 ) close( rt_fdr );
    unlink( RT__FIFO_RD );
}

static void rt_destroy_fifo_wr( void ){
    if( rt_fdw != -1 ) close( rt_fdw );
    unlink( RT__FIFO_WR );
}

static void rt_change_volume( unsigned int tick, float gain, int used_only ){
   int j, i;
   struct track *track;
   signed int new_volume;
   snd_seq_event_t ev;

   snd_seq_ev_clear(&ev);
   ev.queue = queue;
   ev.source.port = 0;
   ev.flags = SND_SEQ_TIME_STAMP_TICK;
   ev.type = SND_SEQ_EVENT_CONTROLLER;
   ev.time.tick = tick;
   ev.data.control.param = 7;

   for (i = 0; i < num_tracks; ++i) {
      track = &tracks[i];
      ev.dest = ports[track->port];
      for( j = 0; j < 16; j++ ) {
         if( track->used[j] || !used_only ) {
            new_volume = gain*track->volume[j];
            if( new_volume > RT__MAX_VOLUME ) new_volume = RT__MAX_VOLUME;
            if( track->fade_volume[j] == -1 || new_volume != track->fade_volume[j] ) {
               ev.data.control.channel = j;
               ev.data.control.value = new_volume;
               rt_send_event(&ev);
               track->fade_volume[j] = new_volume;
            }
         }
      }
   }
}

static void rt_change_prog0( unsigned int tick, char prog0 ){
   int j, i;
   struct track *track;
   signed int new_volume;
   snd_seq_event_t ev;

   snd_seq_ev_clear(&ev);
   ev.queue = queue;
   ev.source.port = 0;
   ev.flags = SND_SEQ_TIME_STAMP_TICK;
   ev.type = SND_SEQ_EVENT_PGMCHANGE;
   ev.time.tick = tick;
   snd_seq_ev_set_fixed(&ev);
   ev.data.control.channel = 0;
   ev.data.control.value = prog0;
   for (i = 0; i < num_tracks; ++i) {
      track = &tracks[i];
      ev.dest = ports[track->port];
      rt_send_event(&ev);
   }
}


static void rt_change_tempo( snd_seq_event_t *ev, struct event* event ){
   int j, i;

   ev->type = SND_SEQ_EVENT_TEMPO;
   ev->time.tick = event->tick+1;
   ev->dest = ports[event->port];

   snd_seq_ev_set_fixed(ev);
   ev->dest.client = SND_SEQ_CLIENT_SYSTEM;
   ev->dest.port = SND_SEQ_PORT_SYSTEM_TIMER;
   ev->data.queue.queue = queue;
   rt_mspqn = (int) (rt_mspqn_req/rt_tempofactor);
   ev->data.queue.param.value = rt_mspqn;
   rt_send_event(ev);
}


static void rt_create_fadeout_profile( int nfade, float *fade_gains ){
   int i, j;
   double heard;
   double min_gain;
   double speed;
   struct track *track;

   int max_vol = 0;
   for (i = 0; i < num_tracks; ++i) {
      track = &tracks[i];
      for( j = 0; j < 16; j++ ) {
         if( track->used[j] ) {
            if( track->volume[j] > max_vol ) {
               max_vol = track->volume[j];
            }
         }
      }
   }

   if( max_vol > 0 ) {
      min_gain = 3.9/max_vol;
      speed = -log( min_gain );
   } else {
      speed = 1.0;
   }

   for( i = 0; i < nfade; i++ ) {
      heard = 0.5*( cos( (((double)i)*RT__PI)/(nfade-1) ) + 1.0 );
      fade_gains[ i ] = exp( speed*( heard - 1.0 ) );
   }
}

static char rt_get_code( void ){
   char code = RT__NULL;;
   if( rt_fdr != -1 ) {
      int istat = read( rt_fdr, &code, 1);
      if( istat < 0 ) {
         rt_error( RT__BAD_FIFO_RD );
         code = RT__ABORT;
      } else if( istat == 0 ) {
         code = RT__NULL;
      }
   }
   return code;
}

static char rt_get_code_blocking( void ){
   char code = rt_get_code();
   while( code == RT__NULL && !rt_terminate ) {
      sleep(1);
      code = rt_get_code();
   }
   return code;
}

static char rt_cmd( void ){
   char code = rt_get_code();

   if( code == RT__PLAY ) {
      int len;
      char *ps = rt_playlist + rt_song_w*RT__SONG_LEN;
      char *ps0 = rt_playlist + rt_song_w*RT__SONG_LEN;

      for( len = 0; len < RT__NVAL; len++ ) {
         *(ps++) = rt_get_code();
      }

      *ps = rt_get_code();
      while( *ps != 0 && !rt_terminate ) {
         if( ++len < RT__SONG_LEN ) {
            *(++ps) = rt_get_code_blocking();
         } else {
            rt_error( RT__SONG_TOO_LONG );
            break;
         }
      }

      if( ++rt_song_w == RT__MAX_SONG ) rt_song_w = 0;
      if( ++rt_nsong > RT__MAX_SONG ) rt_error( RT__SONG_OOB_P );

      if( rt_verbose ) printf("aplaymidi: que '%s' (instrument:%d transpose:%d speed:%d)\n",
                              ps0+RT__NVAL, ps0[0], ps0[1], ps0[2] );

   } else if( code == RT__PROG0 ) {
      rt_inst = rt_get_code();
      if( rt_verbose ) printf("aplaymidi: Changing prog0 to %d\n", rt_inst );

   } else if( code == RT__TRANS ) {
      rt_tran = rt_get_code();
      if( rt_verbose ) printf("aplaymidi: Changing transposition to %d\n", rt_tran );

   } else if( code == RT__TEMPO ) {
      rt_tempofactor = pow( 2.0, rt_get_code()/99.0 );
      if( rt_verbose ) printf("aplaymidi: Changing tempo factor to %g\n", rt_tempofactor );

   } else if( code == RT__TERM ) {
      if( rt_verbose ) printf("aplaymidi: Terminating player\n");
      rt_terminate = 1;
      code = RT__ABORT;

   } else if( code == RT__EMPTY ) {
      if( rt_verbose ) printf("aplaymidi: Emptying playlist\n");
      rt_song_r = 0;
      rt_song_w = 0;
      rt_nsong = 0;

   } else if( rt_verbose && code != RT__NULL ) {
      if( rt_verbose ) printf("aplaymidi: Got code '%c'\n", code );
   }

   if( rt_terminate ) code = RT__ABORT;
   return code;
}

static void rt_error( int error ) {
   perror( rt_message[ error ] );
   rt_terminate = 1;
}

static int rt_pop_file( void ){
   int result = 0;
   if( rt_nsong > 0 ) {
      char *ps = rt_playlist + rt_song_r*RT__SONG_LEN;
      rt_inst = *(ps++);
      rt_tran = *(ps++);
      rt_tempofactor = pow( 2.0, *(ps++)/99.0 );
      file_name = ps;
      if( ++rt_song_r == RT__MAX_SONG ) rt_song_r = 0;
      if( --rt_nsong < 0 ) {
         rt_error( RT__SONG_OOB_N );
      } else {
         if( rt_verbose ) printf("aplaymidi: playing '%s' (instrument:%d transpose:%d tempo:%g)\n",
                                  file_name, rt_inst, rt_tran, rt_tempofactor );
         result = 1;
      }
   }
   return result;
}



static void rt_send_reply( char code, const char *text ) {
   if( rt_fdw != -1 ) {
      if( write( rt_fdw, &code, 1 ) != 1 ) {
         rt_error( RT__BAD_FIFO_WR );
      } else if( text ){
         size_t len = strlen( text ) + 1;
         if( write( rt_fdw, text, len ) != len ) {
            rt_error( RT__BAD_FIFO_WR );
         } else {
            printf("aplaymidi: sent reply code %c (%s)\n", code,text );
         }
      } else {
         printf("aplaymidi: sent reply code %c\n", code );
      }
   }
}


/* All notes off and sustain pedal up for all chanels in all tracks. */
static void rt_all_notes_off( snd_seq_event_t *ev ){
   int i, j;

   ev->type = SND_SEQ_EVENT_CONTROLLER;

   for (i = 0; i < num_tracks; ++i){
      struct track *track = &tracks[i];
      struct event *e2 = track->current_event;
      if( e2 ) {
         ev->dest = ports[e2->port];
         for (j = 0; j < 16; j++ ){
            snd_seq_ev_set_fixed(ev);
            ev->data.control.channel = j;
            ev->data.control.param = 123;
            ev->data.control.value = 0;
            rt_send_event(ev);
            ev->data.control.param = 64;
            rt_send_event(ev);
         }
      }
   }
}




