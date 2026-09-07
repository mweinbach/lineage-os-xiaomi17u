// SPDX-License-Identifier: Apache-2.0
// Compile-only declarations. The unchanged factory JAR provides all runtime IPC code.
package com.miui.cameraopt;

import android.content.ComponentName;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.os.IInterface;
import android.os.RemoteException;

public interface ICameraOptManager extends IInterface {
    void adjBoost(String arg0, int arg1, long arg2, int arg3) throws RemoteException;
    void boostCameraByThreshold(long arg0) throws RemoteException;
    String getSecretKey() throws RemoteException;
    String getSystemStatusJson(int arg0) throws RemoteException;
    boolean getVerifyResult() throws RemoteException;
    boolean interceptAppRestartIfNeeded(String arg0, String arg1, int arg2, int arg3) throws RemoteException;
    boolean isCameraInForeground() throws RemoteException;
    boolean isCameraScene() throws RemoteException;
    boolean isHasCaptureTask() throws RemoteException;
    void notify3rdAppProviderUsed(String arg0, String arg1) throws RemoteException;
    void notifyActivityChanged(ComponentName arg0) throws RemoteException;
    void notifyActivityDisplayChange(int arg0, int arg1, String arg2, String arg3, String arg4, int arg5, int arg6, int arg7, int arg8) throws RemoteException;
    void notifyActivityStart(Intent arg0) throws RemoteException;
    void notifyActivityStateChange(int arg0, int arg1, String arg2, String arg3, String arg4, int arg5, int arg6, int arg7) throws RemoteException;
    void notifyCameraPerformanceTime(String arg0, String arg1, long arg2) throws RemoteException;
    void notifyCameraPostProcessState() throws RemoteException;
    void notifyCameraStatusChanged(String arg0, String arg1, String arg2, int arg3, int arg4, int arg5) throws RemoteException;
    void notifyFocusWindowChanged(int arg0, int arg1, int arg2, String arg3) throws RemoteException;
    void notifyProcessDied(int arg0, int arg1, String arg2, String arg3) throws RemoteException;
    void notifyProcessStarted(int arg0, int arg1, String arg2, String arg3) throws RemoteException;
    void notifyStartActivityFinish(Intent arg0, int arg1, long arg2, long arg3) throws RemoteException;
    void onTransitionAnimateStateChanged(boolean arg0, int arg1) throws RemoteException;
    void reclaimMemoryForCamera(long arg0, int arg1, int arg2) throws RemoteException;
    void relayoutWindow(int arg0, int arg1, int arg2, String arg3, String arg4, int arg5, int arg6, int arg7, int arg8, int arg9, int arg10) throws RemoteException;
    void removeWindow(int arg0, int arg1, int arg2, String arg3, String arg4) throws RemoteException;
    void reportMemPressure(int arg0) throws RemoteException;
    void sendCameraEvent(int arg0, String arg1) throws RemoteException;
    void updateCloudData(double arg0, String arg1) throws RemoteException;

    abstract class Stub extends Binder implements ICameraOptManager {
        public Stub() {
            throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
        }

        @Override
        public IBinder asBinder() {
            throw new UnsupportedOperationException("Compile-only CameraOpt API declaration");
        }
    }
}
