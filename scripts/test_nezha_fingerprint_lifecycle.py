#!/usr/bin/env python3
"""Run deterministic Java lifecycle fixtures for the pinned Nezha bridge, without a phone.

Uses a local JDK and API doubles to exercise lifecycle behavior. Separately compile
against selected Android headers/build services; these doubles are not platform proof.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

WORKSPACE = Path(__file__).resolve().parents[1]


def source_from_patch(workspace=WORKSPACE):
    metadata = json.loads((workspace / "patches/evolution/nezha-fingerprint-overlay-lifecycle.json").read_text())
    patch = (workspace / metadata["patch"]).read_bytes()
    if hashlib.sha256(patch).hexdigest() != metadata["patch_sha256"]:
        raise ValueError("Fingerprint patch digest mismatch")
    target = next(row for row in metadata["files"] if row["path"].endswith("/NezhaFingerprintOverlay.java"))
    marker = "+++ b/" + target["path"] + "\n"
    body = patch.decode().split(marker, 1)[1].split("diff --git ", 1)[0]
    source = "".join(line[1:] for line in body.splitlines(keepends=True) if line.startswith("+") and not line.startswith("+++"))
    if hashlib.sha256(source.encode()).hexdigest() != target["after_sha256"]:
        raise ValueError("Fingerprint helper digest mismatch")
    return source


def run_validation(root, source):
    files={
    'android/os/Build.java':'package android.os; public class Build { public static String DEVICE="nezha"; }',
    'android/os/SystemProperties.java':'package android.os; public class SystemProperties { public static String value="2.0"; public static String get(String key){return value;} }',
    'android/os/Looper.java':'package android.os; public class Looper {}',
    'android/os/HandlerThread.java':'package android.os; public class HandlerThread {public HandlerThread(String n){} public void start(){} public Looper getLooper(){return new Looper();}}',
    'android/os/Handler.java':'''package android.os; import java.util.*; public class Handler { public static Queue<Runnable> tasks=new ArrayDeque<>(); public Handler(Looper l){} public boolean post(Runnable r){tasks.add(r); return true;} public static void drain(){while(!tasks.isEmpty())tasks.remove().run();}}''',
    'android/os/RemoteException.java':'package android.os; public class RemoteException extends Exception {public RemoteException(String s){super(s);}}',
    'android/os/IBinder.java':'''package android.os; public interface IBinder {int FIRST_CALL_TRANSACTION=1; interface DeathRecipient {void binderDied();} void linkToDeath(DeathRecipient d,int f)throws RemoteException; boolean unlinkToDeath(DeathRecipient d,int f); boolean transact(int c,Parcel d,Parcel r,int f)throws RemoteException;}''',
    'android/os/Parcel.java':'''package android.os; import java.util.*; public class Parcel { public static int live=0; public String token; public List<Integer> ints=new ArrayList<>(); public static Parcel obtain(){live++;return new Parcel();} public void writeInterfaceToken(String t){token=t;} public void writeInt(int i){ints.add(i);} public void readException(){} public int readInt(){return 0;} public void recycle(){live--;}}''',
    'android/os/ServiceManager.java':'package android.os; public class ServiceManager {public static IBinder service; public static IBinder checkService(String s){return service;}}',
    'android/util/Slog.java':'package android.util; public class Slog {public static void w(String t,String s){} public static void w(String t,String s,Throwable e){} public static void e(String t,String s,Throwable e){}}',
    'android/view/Display.java':'''package android.view; public class Display {public static final int DEFAULT_DISPLAY=0, STATE_UNKNOWN=0, STATE_OFF=1, STATE_ON=2, STATE_DOZE=3, STATE_DOZE_SUSPEND=4, STATE_ON_SUSPEND=6; public int state=2; public int getState(){return state;}}''',
    'android/hardware/display/DisplayManager.java':'''package android.hardware.display; import android.os.Handler; import android.view.Display; public class DisplayManager {public interface DisplayListener {void onDisplayChanged(int id);void onDisplayAdded(int id);void onDisplayRemoved(int id);} public Display display=new Display(); public boolean failUnregister=false; public DisplayListener listener; public void registerDisplayListener(DisplayListener l,Handler h){listener=l;} public void unregisterDisplayListener(DisplayListener l){if(failUnregister)throw new RuntimeException("unregister fixture"); if(listener==l)listener=null;} public Display getDisplay(int id){return display;}}''',
    'android/content/Context.java':'''package android.content; import android.hardware.display.DisplayManager; public class Context {public DisplayManager displays=new DisplayManager(); public <T>T getSystemService(Class<T> c){return c.cast(displays);}}''',
    'com/android/server/biometrics/sensors/AcquisitionClient.java':'''package com.android.server.biometrics.sensors; import android.content.Context; public class AcquisitionClient<T> {public Context context=new Context(); public Context getContext(){return context;}}''',
    'com/android/server/biometrics/sensors/EnrollClient.java':'package com.android.server.biometrics.sensors; public class EnrollClient extends AcquisitionClient<Object>{}',
    'com/android/server/biometrics/sensors/AuthenticationClient.java':'package com.android.server.biometrics.sensors; public class AuthenticationClient extends AcquisitionClient<Object>{}',
    'com/android/server/biometrics/sensors/DetectionConsumer.java':'package com.android.server.biometrics.sensors; public interface DetectionConsumer{}',
    'com/android/server/biometrics/sensors/LifecycleHarness.java':'''package com.android.server.biometrics.sensors;
    import android.os.*; import java.util.*; import android.hardware.display.DisplayManager;
    public class LifecycleHarness {
     static int assertions=0;
     static void check(boolean b,String s){assertions++;if(!b)throw new AssertionError(s);}
     static class Detect extends AcquisitionClient<Object> implements DetectionConsumer{}
     static class Binder implements IBinder {
      List<String> calls=new ArrayList<>(); DeathRecipient death; int fail=-1; boolean reject=false; boolean failUnlink=false;
      public void linkToDeath(DeathRecipient d,int f){death=d;}
      public boolean unlinkToDeath(DeathRecipient d,int f){if(failUnlink)throw new NoSuchElementException("unlink fixture");death=null;return true;}
      public boolean transact(int c,Parcel d,Parcel r,int f)throws RemoteException {
       check(c==1 && f==0 && d.token.equals("vendor.xiaomi.hardware.fingerprintextension.IXiaomiFingerprint"),"wire contract");
       calls.add(d.ints.get(0)+":"+d.ints.get(1));
       if(calls.size()==fail)throw new RemoteException("fixture failure");return !reject;
      }
     }
     static Binder fresh(){Binder b=new Binder(); ServiceManager.service=b; return b;}
     public static void main(String[] args){
      AcquisitionClient<?>[] clients={new EnrollClient(),new AuthenticationClient(),new Detect()};
      int[] modes={1,3,7};
      for(int i=0;i<clients.length;i++){
       Binder b=fresh(); var c=clients[i]; var o=NezhaFingerprintOverlay.show(5,c);
       check(b.calls.isEmpty(),"nonblocking start");Handler.drain();
       check(b.calls.equals(List.of("4:"+modes[i],"3:2","1:1")),"start order");
       o.hide();check(b.calls.size()==3,"nonblocking stop");Handler.drain();
       check(b.calls.subList(3,5).equals(List.of("1:0","4:"+(modes[i]+1))),"cleanup order");
       check(c.context.displays.listener==null && b.death==null,"cleanup subscriptions");
       o.hide();Handler.drain();check(b.calls.size()==5,"idempotent stop");
      }
      Binder b=fresh(); EnrollClient c=new EnrollClient(); var o=NezhaFingerprintOverlay.show(5,c);o.hide();Handler.drain();check(b.calls.isEmpty(),"canceled pending start");
      b=fresh(); c=new EnrollClient();o=NezhaFingerprintOverlay.show(5,c);Handler.drain();
      int[] states={1,2,3,4,6,0};int[] powers={0,2,1,3,4,0};
      for(int i=0;i<states.length;i++){c.context.displays.display.state=states[i];o.onDisplayChanged(0);check(b.calls.get(b.calls.size()-1).equals("3:"+powers[i]),"display mode");}
      int count=b.calls.size();o.onDisplayChanged(1);check(b.calls.size()==count,"secondary display ignored");
      o.hide();Handler.drain();o.onDisplayChanged(0);check(b.calls.size()==count+2,"stale callback ignored");
      for(int fail=1;fail<=3;fail++){b=fresh();b.fail=fail;c=new EnrollClient();o=NezhaFingerprintOverlay.show(5,c);Handler.drain();check(c.context.displays.listener==null && b.death==null,"failure subscriptions");check(b.calls.get(b.calls.size()-1).equals("4:2"),"failure stops operation");}
      b=fresh();c=new EnrollClient();o=NezhaFingerprintOverlay.show(5,c);Handler.drain();b.fail=4;o.hide();Handler.drain();check(b.calls.get(4).equals("4:2"),"overlay failure still stops operation");
      b=fresh();c=new EnrollClient();o=NezhaFingerprintOverlay.show(5,c);Handler.drain();b.death.binderDied();Handler.drain();check(c.context.displays.listener==null,"binder death cleanup");
      for(int failure=0;failure<3;failure++){b=fresh();c=new EnrollClient();o=NezhaFingerprintOverlay.show(5,c);Handler.drain();b.failUnlink=failure!=0;c.context.displays.failUnregister=failure!=1;o.hide();Handler.drain();check(b.calls.subList(3,5).equals(List.of("1:0","4:2")),"listener failure still clears hardware");int before=b.calls.size();o.onDisplayChanged(0);o.hide();Handler.drain();check(b.calls.size()==before,"failed listener cannot reactivate operation");}
      ServiceManager.service=null;c=new EnrollClient();o=NezhaFingerprintOverlay.show(5,c);Handler.drain();check(c.context.displays.listener==null,"missing service");o.hide();Handler.drain();
      b=fresh();c=new EnrollClient();Build.DEVICE="other";check(NezhaFingerprintOverlay.show(5,c)==null,"device gate");Build.DEVICE="nezha";
      check(NezhaFingerprintOverlay.show(4,c)==null,"sensor gate");SystemProperties.value="1.0";check(NezhaFingerprintOverlay.show(5,c)==null,"version gate");SystemProperties.value="2.0";
      check(NezhaFingerprintOverlay.show(5,new AcquisitionClient<Object>())==null,"unsupported operation gate");check(b.calls.isEmpty(),"gated calls absent");
      check(Parcel.live==0,"all parcels recycled");System.out.println("PASS: "+assertions+" assertions; lifecycle, mapping, gates, cancellation, binder death, failures, parcel cleanup");
     }
    }'''
    }
    for name,content in files.items():
     dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(content)
    dest=root/'com/android/server/biometrics/sensors/NezhaFingerprintOverlay.java';dest.write_text(source)
    subprocess.run(['javac','-d',str(root/'classes'),*[str(f) for f in root.rglob('*.java')]],check=True)
    subprocess.run(['java','-cp',str(root/'classes'),'com.android.server.biometrics.sensors.LifecycleHarness'],check=True)


def main():
    source = source_from_patch()
    with tempfile.TemporaryDirectory(prefix="nezha-fingerprint-fixture-") as directory:
        run_validation(Path(directory), source)


if __name__ == "__main__":
    main()
