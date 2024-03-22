I added the following to the loader:

- SD and DD support
	In zx0boot.src define sectsiz =$100 or =$80
	Caveat: Due to the added commands to fill DBYTLO/HI, the DD version did not fit in three boot sectors.
	Thus the loader file must start in sector 4!
	I put $004 into DAUX1/2 by reusing the code which sets the disk buffer to $400.

- Support extended RAM to cache a copy of the loader and CONFIG
	- The highest available Axlon bank for 400/800
	- Bank 00 (value of bits 3 and 4 of PORTB) for XEs with 128+KB
		This also survives programs using full 64KB, not only 48KB
	- RAM under the OS for XLs/XEs with 64KB
		Retained only with programs needing only 48KB

- The buffer starts at $400 and zx0boot loads to $480 for SD and to $500 for DD.
	As a result everything including the splash screen fits under $1000.
	Due to this: The DList no longer contains a jump in the middle.

The ATRs contain the additional files you posted in the VCF-ATR today.

Now I need some people who use it regularly to see if everything works in daily use.

cheers
Joachim
