package org.lineageos.aperture.compat;
import java.util.*;
import android.hardware.camera2.CameraManager;
import androidx.camera.core.*;
import androidx.camera.core.concurrent.CameraCoordinator;
import androidx.camera.core.impl.CameraFactory;
import androidx.camera.core.impl.CameraInternal;
import androidx.camera.core.impl.Observable;
public class CameraFactoryHarness {
 static class FakeFactory implements CameraFactory, CameraFactory.Interrogator {
  Set<String> ids=new LinkedHashSet<>(Arrays.asList("0","1","2")); int gets=0; boolean stopped=false;
  public Set<String> getAvailableCameraIds(){return ids;}
  public List<String> getAvailableCameraIds(List<String> input){return new ArrayList<>(input);}
  public void onCameraIdsUpdated(List<String> input){ids=new LinkedHashSet<>(input);}
  public CameraInternal getCamera(String id){gets++;return null;}
  public CameraCoordinator getCameraCoordinator(){return null;}
  public Object getCameraManager(){return this;}
  public Observable<List<CameraIdentifier>> getCameraPresenceSource(){return null;}
  public void shutdown(){stopped=true;}
 }
 static int checks=0;
 static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
 public static void main(String[] args)throws Exception {
  CameraManager manager=new CameraManager();manager.capabilities.put("0",new int[]{0,11});
  manager.capabilities.put("1",new int[]{4,6,7,14});manager.capabilities.put("2",new int[]{4,6,7,14});
  FakeFactory factory=new FakeFactory();NezhaCameraFactory filtered=new NezhaCameraFactory(factory,manager);
  check(filtered.getAvailableCameraIds().equals(Collections.singleton("0")),"retain logical0 only");
  check(factory.ids.equals(Collections.singleton("0")),"coordinator/delegate sees filtered set");
  check(factory.gets==0,"constructing filter never builds CameraInternal");
  check(manager.capabilities.get("0")[1]==11,"logical capability unchanged");
  try{filtered.getCamera("1");throw new AssertionError("system camera admitted");}catch(CameraUnavailableException expected){}
  check(factory.gets==0,"system camera not forwarded");filtered.getCamera("0");check(factory.gets==1,"public camera forwarded");
  manager.capabilities.put("external",new int[]{0});manager.capabilities.put("mixed",new int[]{0,14});
  filtered.onCameraIdsUpdated(Arrays.asList("0","1","2","external","mixed","missing","error"));
  check(filtered.getAvailableCameraIds().equals(new LinkedHashSet<>(Arrays.asList("0","external"))),"presence filters malformed and system cameras, keeps valid external");
  check(filtered.getAvailableCameraIds(Arrays.asList("1","0","2")).equals(Collections.singletonList("0")),"interrogator filter");
  check(filtered.getCameraManager()==factory,"original manager preserved");
  filtered.onCameraIdsUpdated(Arrays.asList("1","2","missing","error"));
  check(filtered.getAvailableCameraIds().isEmpty(),"no fallback when no valid cameras");
  check(!NezhaCameraFactory.admits(null),"null metadata rejected");
  check(!NezhaCameraFactory.admits(new int[]{}),"empty metadata rejected");
  check(NezhaCameraFactory.admits(new int[]{11,0}),"logical public valid");
  check(!NezhaCameraFactory.admits(new int[]{0,14}),"system override rejected");
  filtered.shutdown();check(factory.stopped,"shutdown forwarded");
  System.out.println(checks+" behavioral checks passed");
 }
}
