package com.example.app;

import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
  @Override
  public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);

    registerPlugin(ScreenSharePlugin.class);

    android.webkit.WebView.setWebContentsDebuggingEnabled(true);
    
    WebView wv = this.bridge.getWebView();
    WebSettings s = wv.getSettings();

    // максимум "антикэша"
    s.setCacheMode(WebSettings.LOAD_NO_CACHE);
    s.setDomStorageEnabled(true);

    wv.clearCache(true);
    wv.clearHistory();

    // важно: принудительно грузим без кеша (для текущего запуска)
    wv.reload();
    wv.loadUrl("https://nex2ilo.com");
  }
}
