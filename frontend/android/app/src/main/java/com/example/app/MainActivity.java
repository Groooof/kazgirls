package com.example.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.example.app.screenshare.ScreenSharePlugin;

public class MainActivity extends BridgeActivity {
    
    @Override
    public void onCreate(Bundle savedInstanceState) {
        // 1. Регистрируем плагин
        registerPlugin(ScreenSharePlugin.class);

        // 2. Инициализируем мост
        super.onCreate(savedInstanceState);

        // 3. Безопасная очистка кэша (с проверкой на null)
        if (this.getBridge() != null && this.getBridge().getWebView() != null) {
            this.getBridge().getWebView().clearCache(true);
            this.getBridge().getWebView().clearHistory();
        }
    }
}