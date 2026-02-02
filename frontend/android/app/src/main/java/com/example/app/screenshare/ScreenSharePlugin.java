package com.example.app.screenshare;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.util.DisplayMetrics;
import android.view.WindowManager;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.JSObject;

import org.webrtc.*;

import java.util.Arrays;
import java.util.List;

@CapacitorPlugin(name = "ScreenShare")
public class ScreenSharePlugin extends Plugin {

    private static final int REQUEST_CODE = 5001;

    private MediaProjectionManager projectionManager;
    private PeerConnectionFactory factory;
    private PeerConnection peerConnection;
    private EglBase eglBase;
    
    // Храним ссылки, чтобы GC не убил их и чтобы потом закрыть
    private VideoSource videoSource;
    private ScreenCapturerAndroid capturer;

    private PluginCall savedCall;

    @Override
    public void load() {
        Context ctx = getContext();

        PeerConnectionFactory.initialize(
            PeerConnectionFactory.InitializationOptions.builder(ctx).createInitializationOptions()
        );

        eglBase = EglBase.create();

        factory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(new DefaultVideoEncoderFactory(eglBase.getEglBaseContext(), true, true))
            .setVideoDecoderFactory(new DefaultVideoDecoderFactory(eglBase.getEglBaseContext()))
            .createPeerConnectionFactory();

        projectionManager = (MediaProjectionManager) ctx.getSystemService(Context.MEDIA_PROJECTION_SERVICE);
    }

    @PluginMethod
    public void start(PluginCall call) {
        savedCall = call;
        Intent intent = projectionManager.createScreenCaptureIntent();
        startActivityForResult(call, intent, REQUEST_CODE);
    }

    @ActivityCallback
    private void screenCaptureResult(PluginCall call, int resultCode, Intent data) {
        if (resultCode != Activity.RESULT_OK || data == null) {
            call.reject("Screen permission denied");
            return;
        }

        // 1. Запускаем сервис уведомления (ОБЯЗАТЕЛЬНО для Android 10+)
        startForegroundService();

        // 2. Задержка и старт WebRTC
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
            try {
                // ВАЖНО: Мы НЕ вызываем projectionManager.getMediaProjection здесь вручную!
                // Мы передаем сырой 'data' в startWebRTC
                startWebRTC(data);
            } catch (Exception e) {
                call.reject("Java Error: " + e.getMessage());
            }
        }, 500);
    }

    private void startWebRTC(Intent data) {
        List<PeerConnection.IceServer> iceServers = Arrays.asList(
            PeerConnection.IceServer.builder("stun:nex2ilo.com:3478").createIceServer(),
            PeerConnection.IceServer.builder("turn:nex2ilo.com:3478")
                .setUsername("kazgirls")
                .setPassword("9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN")
                .createIceServer()
        );

        PeerConnection.RTCConfiguration rtcConfig = new PeerConnection.RTCConfiguration(iceServers);
        
        // ВАЖНО: Unified Plan — современный стандарт
        rtcConfig.sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN;

        peerConnection = factory.createPeerConnection(rtcConfig, new PeerConnection.Observer() {
            @Override public void onIceCandidate(IceCandidate candidate) {
                if (savedCall == null) return;
                JSObject obj = new JSObject();
                obj.put("candidate", candidate.sdp);
                obj.put("sdpMid", candidate.sdpMid);
                obj.put("sdpMLineIndex", candidate.sdpMLineIndex);
                notifyListeners("onIceCandidate", obj);
            }
            @Override public void onIceConnectionChange(PeerConnection.IceConnectionState s) {}
            @Override public void onConnectionChange(PeerConnection.PeerConnectionState s) {}
            @Override public void onSignalingChange(PeerConnection.SignalingState s) {}
            @Override public void onIceConnectionReceivingChange(boolean b) {}
            @Override public void onIceGatheringChange(PeerConnection.IceGatheringState s) {}
            @Override public void onIceCandidatesRemoved(IceCandidate[] c) {}
            @Override public void onAddStream(MediaStream stream) {}
            @Override public void onRemoveStream(MediaStream stream) {}
            @Override public void onDataChannel(DataChannel dc) {}
            @Override public void onRenegotiationNeeded() {}
            @Override public void onAddTrack(RtpReceiver r, MediaStream[] s) {}
        });

        // --- Настройка ScreenCapturer ---
        // Передаем data (Intent) внутрь ScreenCapturerAndroid
        capturer = new ScreenCapturerAndroid(data, new MediaProjection.Callback() {
            @Override public void onStop() {
                // Если запись остановилась системой
            }
        });

        SurfaceTextureHelper textureHelper =
            SurfaceTextureHelper.create("ScreenCaptureThread", eglBase.getEglBaseContext());

        videoSource = factory.createVideoSource(true); // isScreencast = true
        capturer.initialize(textureHelper, getContext(), videoSource.getCapturerObserver());

        // Получаем реальное разрешение экрана
        WindowManager wm = (WindowManager) getContext().getSystemService(Context.WINDOW_SERVICE);
        DisplayMetrics metrics = new DisplayMetrics();
        wm.getDefaultDisplay().getRealMetrics(metrics);
        
        // Запускаем захват
        capturer.startCapture(metrics.widthPixels, metrics.heightPixels, 30);

        VideoTrack videoTrack = factory.createVideoTrack("SCREEN_TRACK", videoSource);
        peerConnection.addTrack(videoTrack); // Используем addTrack для Unified Plan

        // --- Создание Offer ---
        peerConnection.createOffer(new SdpObserver() {
            @Override
            public void onCreateSuccess(SessionDescription sdp) {
                peerConnection.setLocalDescription(this, sdp);

                if (savedCall != null) {
                    JSObject ret = new JSObject();
                    ret.put("type", sdp.type.canonicalForm());
                    ret.put("sdp", sdp.description);
                    savedCall.resolve(ret);
                }
            }
            
            // ВАЖНО: Возвращаем ошибку в JS, если оффер не создался
            @Override public void onCreateFailure(String s) {
                if (savedCall != null) savedCall.reject("WebRTC CreateOffer Failed: " + s);
            }
            @Override public void onSetFailure(String s) {
                 if (savedCall != null) savedCall.reject("WebRTC SetLocalDescription Failed: " + s);
            }
            @Override public void onSetSuccess() {}
        }, new MediaConstraints());
    }

    @PluginMethod
    public void setRemoteDescription(PluginCall call) {
        String sdp = call.getString("sdp");
        if (peerConnection == null) {
            call.reject("PeerConnection is not initialized");
            return;
        }
        SessionDescription answer = new SessionDescription(SessionDescription.Type.ANSWER, sdp);
        peerConnection.setRemoteDescription(new SdpObserver() {
            @Override public void onSetSuccess() {}
            @Override public void onSetFailure(String s) {}
            @Override public void onCreateSuccess(SessionDescription sdp) {}
            @Override public void onCreateFailure(String s) {}
        }, answer);
        call.resolve();
    }

    @PluginMethod
    public void addIceCandidate(PluginCall call) {
        if (peerConnection == null) {
             call.resolve(); 
             return;
        }
        IceCandidate c = new IceCandidate(
            call.getString("sdpMid"),
            call.getInt("sdpMLineIndex"),
            call.getString("candidate")
        );
        peerConnection.addIceCandidate(c);
        call.resolve();
    }

    private void startForegroundService() {
        Context context = getContext();
        Intent serviceIntent = new Intent(context, ScreenShareService.class);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent);
        } else {
            context.startService(serviceIntent);
        }
    }

    private void stopForegroundService() {
        Context context = getContext();
        Intent serviceIntent = new Intent(context, ScreenShareService.class);
        context.stopService(serviceIntent);
    }

    @PluginMethod
    public void stop(PluginCall call) {
        try {
            if (capturer != null) {
                capturer.stopCapture();
                capturer.dispose();
                capturer = null;
            }
            if (videoSource != null) {
                videoSource.dispose();
                videoSource = null;
            }
            if (peerConnection != null) {
                peerConnection.close();
                peerConnection = null;
            }
        } catch (Exception e) {
            // ignore
        }
        stopForegroundService();
        call.resolve();
    }
}