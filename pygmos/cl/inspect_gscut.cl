procedure inspect_gscut (inimage, mosaic, secfile)

string inimage  {prompt="Output of gscut"}
string mosaic   {prompt="Output of gmosaic"}
string secfile  {prompt="Image sections file created by gscut"}

begin

    display(mosaic//"[sci,1]", 1, zs-, zr+)

    del inimage//"_lo.coords"
    del inimage//"_hi.coords"

    real x1,x2,y1,y2,xcen
    int ids
    for(i=1;i<=100;i+=1)
    {
        tprint(inimage//".fits[MDF]", prparam-, prdata+, showrow-, showhdr-,
               showunits-, rows=i, col="slitid,secx1,secx2,secy1,secy2") \
            | scan(ids, x1, x2, y1, y2)
        xcen=(x1+x2)/2.
        printf("%4d %4d %3d\n", int(xcen), int(y1), ids, \
               >> inimage//"_lo.coords")
        printf("%4d %4d %3d\n", int(xcen), int(y2), ids, \
               >> inimage//"_hi.coords")
    }

    tvmark(1, inimage//"_lo.coords", mark="point", color=204, length=1, lab+, \
           pointsize=2, nxoffset=5, nyoffset=5, txsize=1)
    tvmark(1, inimage//"_hi.coords", mark="point", color=204, length=1, lab-, \
           pointsize=2, nxoffset=5, nyoffset=5, txsize=1)

end
