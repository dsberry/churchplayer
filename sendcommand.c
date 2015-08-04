#include <stdio.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#define RT__FIFO "/tmp/churchplayerfifo_rd"

/* Usage:

% sendcommand code [file|instr] [trans] [instr] [tempo]

where:
   code is a single character code for the command to be executed
   file is the path to a file to be played (only used if code is 'p')
   trans is the number of semit-tones to transpose (only used if code is 'p')
   instr is the GM index of the instrument to be used (only used if code
         is 'p' or 'i')
   tempo is the tempo factor (-99=half speed +99=double speed - only used
         if code is 'p' or 'm')
*/

int main(int argc, char *argv[] ) {
    int fd;
    char c;

    fd = open( RT__FIFO, O_WRONLY );
    write( fd, argv[1], 1 );

    if( *argv[1] == 'p' ) {
       char tran, inst, tempo;

       if( argc > 3 ) {
          tran = atoi( argv[ 3 ] );
       } else {
          tran = 0;
       }

       if( argc > 4 ) {
          inst = atoi( argv[ 4 ] );
       } else {
          inst = -1;
       }

       if( argc > 5 ) {
          tempo = atoi( argv[ 5 ] );
       } else {
          tempo = 0;
       }

       write( fd, &inst, 1 );
       write( fd, &tran, 1 );
       write( fd, &tempo, 1 );
       write( fd, argv[2], strlen( argv[2] ) + 1 );

    } else if( *argv[1] == 'i' ) {
       char inst = atoi( argv[ 2 ] );
       write( fd, &inst, 1 );

    } else if( *argv[1] == 'r' ) {
       char trans = atoi( argv[ 2 ] );
       write( fd, &trans, 1 );

    } else if( *argv[1] == 'm' ) {
       char tempo = atoi( argv[ 2 ] );
       write( fd, &tempo, 1 );

    }

    close(fd);
    return 0;
}
