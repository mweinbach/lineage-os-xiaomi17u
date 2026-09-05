package android.hardware.camera2;
import java.util.Map; import java.util.HashMap;
public final class CameraManager {
 public final Map<String,int[]> capabilities=new HashMap<>();
 public CameraCharacteristics getCameraCharacteristics(String id) throws CameraAccessException {
  if(id.equals("error"))throw new CameraAccessException(0);
  return new CameraCharacteristics(capabilities.get(id));
 }
}
