package android.hardware.camera2;
public final class CameraCharacteristics {
 public static final int REQUEST_AVAILABLE_CAPABILITIES_BACKWARD_COMPATIBLE=0;
 public static final int REQUEST_AVAILABLE_CAPABILITIES_SYSTEM_CAMERA=14;
 public static final Key<int[]> REQUEST_AVAILABLE_CAPABILITIES=new Key<>();
 public static class Key<T> {}
 private final int[] capabilities;
 public CameraCharacteristics(int[] capabilities){this.capabilities=capabilities;}
 @SuppressWarnings("unchecked") public <T>T get(Key<T> key){return (T)capabilities;}
}
