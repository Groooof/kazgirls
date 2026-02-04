package com.example.app;

import android.os.Bundle;
import android.webkit.WebView; // Добавь этот импорт
import com.getcapacitor.BridgeActivity;
import com.example.app.screenshare.ScreenSharePlugin;

public class MainActivity extends BridgeActivity {
    protected void onCreate(Bundle savedInstanceState) {
        // 1. Сначала регистрируем плагин!
        registerPlugin(ScreenSharePlugin.class);

        // 2. И только потом запускаем Capacitor
        super.onCreate(savedInstanceState);

        // 2. ЖЕСТКАЯ ОЧИСТКА КЭША
        // Это гарантирует, что загрузится свежий билд из assets
        this.getBridge().getWebView().clearCache(true);
        this.getBridge().getWebView().clearHistory();
    }
}