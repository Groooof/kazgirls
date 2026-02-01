package com.example.app;

import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    // Получаем WebView
    WebView wv = this.bridge.getWebView();
    
    // Включаем JS и доступ к файлам
    WebSettings s = wv.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setAllowFileAccess(true);
    s.setAllowContentAccess(true);
    s.setMediaPlaybackRequiresUserGesture(false);

    // Разрешаем WebRTC (камера/экран)
    wv.setWebChromeClient(new WebChromeClient() {
        @Override
        public void onPermissionRequest(final PermissionRequest request) {
            request.grant(request.getResources());
        }
    });
  }
}