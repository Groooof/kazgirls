package com.example.app.screenshare;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

public class ScreenShareService extends Service {
    public static final String CHANNEL_ID = "ScreenShareChannel";
    public static final int NOTIFICATION_ID = 12345;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // Создаем уведомление
        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Стриминг экрана")
                .setContentText("Ваш экран транслируется...")
                .setSmallIcon(android.R.drawable.ic_menu_camera) // Замени на свою иконку, если есть
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build();

        // Запускаем сервис в Foreground режиме.
        // Это КРИТИЧЕСКИ важно для типа mediaProjection
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }

        return START_NOT_STICKY;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel serviceChannel = new NotificationChannel(
                    CHANNEL_ID,
                    "Screen Share Service",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(serviceChannel);
            }
        }
    }
}