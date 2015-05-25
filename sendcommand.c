#include <stdio.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#define RT__FIFO "/tmp/churchplayerfifo_rd"

/* Usage:

% sendcommand code [file] [trans] [intr]

where:
   code is a single character code for the command to be executed
   file is the path to a file to be played (only used if code is 'p')
   trans is the number of semit-tones to transpose (only used if code is 'p')
   instr is the GM index of the instrument to be used (only used if code is 'p')
*/

int main(int argc, char *argv[] ) {
    int fd;
    char c;

    fd = open( RT__FIFO, O_WRONLY );
    write( fd, argv[1], 1 );

    if( *argv[1] == 'p' ) {
       char tran, inst;

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

       write( fd, &inst, 1 );
       write( fd, &tran, 1 );
       write( fd, argv[2], strlen( argv[2] ) + 1 );
    }

    close(fd);
    return 0;
}
