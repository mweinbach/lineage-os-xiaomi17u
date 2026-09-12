package org.evolution.nezha.esimprobe;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class StopReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        HoldActivity.stopCurrent();
    }
}
