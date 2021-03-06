procedure align (input)

string input 
string *list

# this script takes as input the FITS image output of `gstransform` and
# outputs the same FITS image, overwritten with all slits aligned to the
# same wavelength range starting at 4000 Angstrom.

begin 
	string name = "shifted"
	string imfinal
	string nombre
	string over

	cache imextensions
	imextensions (input, output="none")
#	printf ("%s\n", input)
#	printf ("%d\n", imext.nimages)

	for (i=1; i<=(imext.nimages); i=i+1) {
		imfinal = input//"[SCI,"//i
#		printf ("%s\n", imfinal + "]")

		imgets (imfinal + "]", "CRVAL1")
		x=real(imgets.value)
#		printf ("%s\n", x)

		imgets (imfinal + "]", "CD1_1")
		y=real(imgets.value)
#		printf ("%s\n", y)

		z = (x-4000)/y
#		printf ("%s\n", z)	

		nombre = name + i
#		printf ("%s\n", nombre)	
	
		imshift (imfinal + "]", nombre, z, 0)	
		over = imfinal + ",overwrite]"	
#		printf ("%s\n", over)
		imcopy (nombre, over, verbose-)
		hedit (imfinal + "]", fields="EXTNAME", value="SCI", add+, verify-, show-)
	}

	
end

