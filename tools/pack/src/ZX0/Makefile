# CC = owcc
# CFLAGS  = -ox -ob -ol+ -onatx -oh -zp8 -fp6 -g0 -Ot -oe -ot -Wall -xc -s -finline-functions -finline-intrinsics -finline-math -floop-optimize -frerun-optimizer -fno-stack-check -march=i386 -mtune=i686
# RM = del
# EXTENSION = .exe
CC = gcc
CFLAGS  = -Wall -Ofast -finline-functions
RM = rm -f

all: zx0 dzx0

zx0: zx0.c optimize.c compress.c memory.c zx0.h
	$(CC) $(CFLAGS) -o zx0 zx0.c optimize.c compress.c memory.c

dzx0: dzx0.c
	$(CC) $(CFLAGS) -o dzx0 dzx0.c

clean:
	$(RM) *.o zx0 dzx0
