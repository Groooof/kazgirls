package com.example.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.media.projection.MediaProjectionManager;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "ScreenShare")
public class ScreenSharePlugin extends Plugin {

  private static final int REQ_CODE = 9211;
  private PluginCall savedCall;

  @PluginMethod
  public void start(PluginCall call) {
    Activity activity = getActivity();
    if (activity == null) {
      call.reject("No activity");
      return;
    }

    MediaProjectionManager mgr =
      (MediaProjectionManager) activity.getSystemService(Context.MEDIA_PROJECTION_SERVICE);

    if (mgr == null) {
      call.reject("MediaProjectionManager is null");
      return;
    }

    savedCall = call;
    Intent intent = mgr.createScreenCaptureIntent();
    startActivityForResult(call, intent, REQ_CODE);
  }

  @Override
  protected void handleOnActivityResult(int requestCode, int resultCode, Intent data) {
    super.handleOnActivityResult(requestCode, resultCode, data);

    if (requestCode != REQ_CODE) return;
    if (savedCall == null) return;

    if (resultCode != Activity.RESULT_OK || data == null) {
      savedCall.reject("User cancelled");
      savedCall = null;
      return;
    }

    JSObject ret = new JSObject();
    ret.put("ok", true);
    savedCall.resolve(ret);
    savedCall = null;
  }
}
