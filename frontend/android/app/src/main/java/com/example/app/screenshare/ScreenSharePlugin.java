package com.example.app.screenshare;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.JSObject;

import androidx.activity.result.ActivityResult;

@CapacitorPlugin(name = "ScreenShare")
public class ScreenSharePlugin extends Plugin {

    private static final String TAG = "ScreenSharePlugin";
    private static ScreenSharePlugin instance;

    @Override
    public void load() {
        super.load();
        instance = this;
    }

    public static void sendEventToJS(String eventName, JSObject data) {
        if (instance != null) {
            instance.notifyListeners(eventName, data);
        }
    }

    @PluginMethod
    public void start(PluginCall call) {
        android.media.projection.MediaProjectionManager manager = 
            (android.media.projection.MediaProjectionManager) getContext().getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        
        Intent intent = manager.createScreenCaptureIntent();
        startActivityForResult(call, intent, "screenCaptureResult");
    }

    @ActivityCallback
    private void screenCaptureResult(PluginCall call, ActivityResult result) {
        int resultCode = result.getResultCode();
        Intent data = result.getData();

        if (resultCode != Activity.RESULT_OK || data == null) {
            call.reject("Permission denied");
            return;
        }

        // Запускаем сервис
        Intent serviceIntent = new Intent(getContext(), ScreenShareService.class);
        serviceIntent.setAction("START");
        serviceIntent.putExtra("RESULT_CODE", resultCode);
        serviceIntent.putExtra("DATA", data);

        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            getContext().startForegroundService(serviceIntent);
        } else {
            getContext().startService(serviceIntent);
        }
        
        JSObject ret = new JSObject();
        ret.put("status", "starting");
        call.resolve(ret);
    }

    @PluginMethod
    public void setRemoteDescription(PluginCall call) {
        String sdp = call.getString("sdp");
        Intent intent = new Intent(getContext(), ScreenShareService.class);
        intent.setAction("SET_REMOTE_DESC");
        intent.putExtra("sdp", sdp);
        getContext().startService(intent);
        call.resolve();
    }

    @PluginMethod
    public void addIceCandidate(PluginCall call) {
        String sdp = call.getString("candidate");
        if (sdp == null) { call.resolve(); return; }
        
        Intent intent = new Intent(getContext(), ScreenShareService.class);
        intent.setAction("ADD_ICE");
        intent.putExtra("candidate", sdp);
        intent.putExtra("sdpMid", call.getString("sdpMid"));
        intent.putExtra("sdpMLineIndex", call.getInt("sdpMLineIndex"));
        getContext().startService(intent);
        call.resolve();
    }

    @PluginMethod
    public void stop(PluginCall call) {
        Intent intent = new Intent(getContext(), ScreenShareService.class);
        intent.setAction("STOP");
        getContext().startService(intent);
        call.resolve();
    }
}