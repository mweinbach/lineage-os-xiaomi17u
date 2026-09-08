import org.lineageos.aperture.compat.NezhaNeutralGainmap;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class NeutralGainmapTest {
    private static int checks;
    private static final String NS = "xmlns:hdrgm=\"http://ns.adobe.com/hdr-gain-map/1.0/\"";
    private static final String PRIMARY = "<rdf:Description " + NS +
            " hdrgm:Version=\"1.0\"><Container:Item Item:Semantic=\"GainMap\"/></rdf:Description>";
    private static final String GAINMAP = "<rdf:Description " + NS +
            " hdrgm:Version=\"1.0\" hdrgm:GainMapMin=\"0\" hdrgm:GainMapMax=\"0\"" +
            " hdrgm:Gamma=\"1\" hdrgm:OffsetSDR=\"0\" hdrgm:OffsetHDR=\"0\"" +
            " hdrgm:HDRCapacityMin=\"0\" hdrgm:HDRCapacityMax=\"0\" hdrgm:BaseRenditionIsHDR=\"False\"/>";
    private static void check(boolean valid) {
        checks++;
        if (!valid) throw new AssertionError("Failed assertion " + checks);
    }
    private static void segment(ByteArrayOutputStream out, int marker, byte[] body) {
        int length=body.length+2;
        out.write(255);out.write(marker);out.write(length>>8);out.write(length&255);out.writeBytes(body);
    }
    private static byte[] iso() {
        byte[] iso=new byte[37];iso[4]=0x48;iso[8]=1;iso[28]=1;return iso;
    }
    // Minimal marker streams exercise the metadata parser, not JPEG decoding.
    // Decoder acceptance is checked separately with retained real captures.
    private static byte[] image(String xmp, byte[] iso) {
        ByteArrayOutputStream out=new ByteArrayOutputStream();out.write(255);out.write(216);
        segment(out,225,("http://ns.adobe.com/xap/1.0/\0"+xmp).getBytes(StandardCharsets.ISO_8859_1));
        if(iso!=null) {
            ByteArrayOutputStream metadata=new ByteArrayOutputStream();
            metadata.writeBytes("urn:iso:std:iso:ts:21496:-1\0".getBytes(StandardCharsets.ISO_8859_1));
            metadata.writeBytes(iso);segment(out,226,metadata.toByteArray());
        }
        segment(out,218,new byte[]{1,1,0,0,63,0});out.write(0);out.write(255);out.write(217);
        return out.toByteArray();
    }
    private static byte[] file(String xmp,byte[] metadata,boolean hasIsoHeader) {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        out.writeBytes(image(PRIMARY,hasIsoHeader ? new byte[4] : null));
        out.writeBytes(image(xmp,metadata));return out.toByteArray();
    }
    private static void rejected(byte[] bytes) {check(NezhaNeutralGainmap.capacityBytes(bytes).length==0);}
    public static void main(String[] args) {
        byte[] original=file(GAINMAP,iso(),true),before=original.clone();
        int[] offsets=NezhaNeutralGainmap.capacityBytes(original);
        check(offsets.length==2);check(Arrays.equals(original,before));
        check(original[offsets[0]]=='0' && original[offsets[1]]==0);
        original[offsets[0]]='1';original[offsets[1]]=1;rejected(original);
        byte[] xmpOnly=file(GAINMAP,null,false);check(NezhaNeutralGainmap.capacityBytes(xmpOnly).length==1);
        rejected(file(GAINMAP,null,true));rejected(file(GAINMAP,iso(),false));
        rejected(null);rejected(new byte[0]);rejected(new byte[NezhaNeutralGainmap.MAX_BYTES+1]);
        for(int i=0;i<before.length;i++) rejected(Arrays.copyOf(before,i));
        for(String field:new String[]{"GainMapMin","GainMapMax","Gamma","OffsetSDR","OffsetHDR","HDRCapacityMin","HDRCapacityMax"}) {
            String pattern="hdrgm:"+field+"=\"";
            int start=GAINMAP.indexOf(pattern)+pattern.length();
            rejected(file(GAINMAP.substring(0,start)+"2"+GAINMAP.substring(start+1),iso(),true));
            rejected(file(GAINMAP.replace("/>"," hdrgm:"+field+"=\"0\"/>"),iso(),true));
        }
        for(int i=0;i<37;i++) {byte[] wrong=iso();wrong[i]^=1;rejected(file(GAINMAP,wrong,true));}
        rejected(file(GAINMAP.replace("False","True"),iso(),true));
        rejected(file(GAINMAP.replace("hdr-gain-map/1.0/","hdr-gain-map/2.0/"),iso(),true));
        byte[] broken=before.clone();broken[4]=(byte)255;broken[5]=(byte)255;rejected(broken);
        check(NezhaNeutralGainmap.capacityBytes(before).length==2);
        System.out.println(checks+" assertions passed");
    }
}
