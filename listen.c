#include <stdio.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#define RT__FIFO "/tmp/churchplayerfifo_wr"

int main(int argc, char *argv[] ) {
    int fd;
    int istat;
    char c;
    char buf[1000];
    char *p;

    fd = open( RT__FIFO, O_RDONLY );

    while( istat = read( fd, &c, 1 ) ) {
       if( c == 'p' ) {
          p = buf;
          while( istat = read( fd, p, 1 ) ) {
             if( istat < 0 || *p == 0 ) break;
             p++;
          }
          if( istat < 0 ) break;
          printf("Playing %s\n", buf );
       } else if( c == 's' ) {
          printf("Stopped\n" );
       }
    }

    close(fd);
    return 0;
}
