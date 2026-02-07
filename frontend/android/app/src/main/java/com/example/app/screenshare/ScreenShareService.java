package com.example.app.screenshare;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import androidx.core.app.NotificationCompat;
import android.util.Log;
import android.util.DisplayMetrics;
import android.view.WindowManager;

import com.getcapacitor.JSObject;

import org.webrtc.*;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ScreenShareService extends Service {
    
    public static final String CHANNEL_ID = "ScreenShare_Final";
    public static final int NOTIFICATION_ID = 101;
    private static final String TAG = "ScreenShareService";

    // --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (Защита от GC) ---
    // Если их убрать внутрь методов -> приложение упадет через 2 секунды
    private PeerConnectionFactory factory;
    private PeerConnection peerConnection;
    private EglBase eglBase;
    private VideoSource videoSource;
    private ScreenCapturerAndroid capturer;
    private SurfaceTextureHelper textureHelper;
    private VideoTrack localVideoTrack; 

    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // 1. СРАЗУ (в первой строке) запускаем Foreground
        startForegroundNotification();

        if (intent == null || intent.getAction() == null) return START_NOT_STICKY;

        String action = intent.getAction();
        Log.d(TAG, "Service Action: " + action);
        
        if ("START".equals(action)) {
            int resultCode = intent.getIntExtra("RESULT_CODE", 0);
            Intent data = intent.getParcelableExtra("DATA");
            if (resultCode != 0 && data != null) {
                executor.execute(() -> initWebRTC(resultCode, data));
            } else {
                stopSelf();
            }
        } 
        else if ("SET_REMOTE_DESC".equals(action)) {
            String sdp = intent.getStringExtra("sdp");
            executor.execute(() -> setRemoteDescription(sdp));
        }
        else if ("ADD_ICE".equals(action)) {
            String sdp = intent.getStringExtra("candidate");
            String mid = intent.getStringExtra("sdpMid");
            int idx = intent.getIntExtra("sdpMLineIndex", 0);
            executor.execute(() -> addIceCandidate(mid, idx, sdp));
        }
        else if ("STOP".equals(action)) {
            executor.execute(this::stopStream);
        }

        return START_STICKY;
    }

    private void startForegroundNotification() {
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Screen Share")
                .setContentText("Live")
                .setSmallIcon(android.R.drawable.ic_menu_camera)
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setOngoing(true);

        int type = 0;
        if (Build.VERSION.SDK_INT >= 29) {
            type = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION;
        }

        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, builder.build(), type);
        } else {
            startForeground(NOTIFICATION_ID, builder.build());
        }
    }

    private void initWebRTC(int resultCode, Intent data) {
        try {
            Log.d(TAG, "Initializing WebRTC (Hardware + No Audio)...");
            Context ctx = getApplicationContext();
            
            PeerConnectionFactory.initialize(
                PeerConnectionFactory.InitializationOptions.builder(ctx)
                    .setEnableInternalTracer(false)
                    .createInitializationOptions()
            );
            
            eglBase = EglBase.create();
            
            // 1. ВОЗВРАЩАЕМ HARDWARE ENCODER (Default)
            // Software (программный) крашил твой телефон сразу. Hardware работал 2 сек.
            VideoEncoderFactory encoderFactory = new DefaultVideoEncoderFactory(eglBase.getEglBaseContext(), true, true);
            VideoDecoderFactory decoderFactory = new DefaultVideoDecoderFactory(eglBase.getEglBaseContext());

            factory = PeerConnectionFactory.builder()
                    .setVideoEncoderFactory(encoderFactory)
                    .setVideoDecoderFactory(decoderFactory)
                    // 2. ОТКЛЮЧАЕМ АУДИО (Чтобы не требовал прав и не крашил движок)
                    .setAudioDeviceModule(null) 
                    .createPeerConnectionFactory();

            List<PeerConnection.IceServer> iceServers = new ArrayList<>();
            iceServers.add(PeerConnection.IceServer.builder("stun:nex2ilo.com:3478").createIceServer());
            iceServers.add(PeerConnection.IceServer.builder("turn:nex2ilo.com:3478")
                .setUsername("kazgirls").setPassword("9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN").createIceServer());
            iceServers.add(PeerConnection.IceServer.builder("turns:nex2ilo.com:5349")
                 .setUsername("kazgirls").setPassword("9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN").createIceServer());

            PeerConnection.RTCConfiguration rtcConfig = new PeerConnection.RTCConfiguration(iceServers);
            rtcConfig.sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN;
            rtcConfig.iceTransportsType = PeerConnection.IceTransportsType.ALL; 
            rtcConfig.bundlePolicy = PeerConnection.BundlePolicy.MAXBUNDLE;

            peerConnection = factory.createPeerConnection(rtcConfig, new PeerConnection.Observer() {
                @Override public void onIceCandidate(IceCandidate candidate) {
                    JSObject obj = new JSObject();
                    obj.put("candidate", candidate.sdp);
                    obj.put("sdpMid", candidate.sdpMid);
                    obj.put("sdpMLineIndex", candidate.sdpMLineIndex);
                    ScreenSharePlugin.sendEventToJS("onIceCandidate", obj);
                }
                @Override public void onIceConnectionChange(PeerConnection.IceConnectionState s) { Log.d(TAG, "ICE: " + s); }
                @Override public void onConnectionChange(PeerConnection.PeerConnectionState s) { Log.d(TAG, "Conn: " + s); }
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

            // --- ЗАХВАТ ---
            capturer = new ScreenCapturerAndroid(data, new android.media.projection.MediaProjection.Callback() {
                @Override public void onStop() { Log.e(TAG, "Projection stopped"); }
            });

            textureHelper = SurfaceTextureHelper.create("ScreenCaptureThread", eglBase.getEglBaseContext());
            videoSource = factory.createVideoSource(true);
            capturer.initialize(textureHelper, ctx, videoSource.getCapturerObserver());

            // 3. РАЗРЕШЕНИЕ qHD (540x960)
            // Идеально для телефонов. Делится на 16. Не перегружает энкодер.
            int width = 540;
            int height = 960;
            
            WindowManager wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
            DisplayMetrics metrics = new DisplayMetrics();
            wm.getDefaultDisplay().getRealMetrics(metrics);
            if (metrics.widthPixels > metrics.heightPixels) {
                width = 960;
                height = 540;
            }

            Log.d(TAG, "Start Capture: " + width + "x" + height);
            capturer.startCapture(width, height, 25); 

            // 4. ТРЕК В ГЛОБАЛЬНУЮ ПЕРЕМЕННУЮ (FIX GC CRASH)
            localVideoTrack = factory.createVideoTrack("ARDAMSv0", videoSource);
            localVideoTrack.setEnabled(true);

            // 5. ИСПОЛЬЗУЕМ TRANSCEIVER С ID (FIX STREAMS: [])
            RtpTransceiver.RtpTransceiverInit init = new RtpTransceiver.RtpTransceiverInit(
                RtpTransceiver.RtpTransceiverDirection.SEND_ONLY,
                Collections.singletonList("ARDAMS")
            );
            peerConnection.addTransceiver(localVideoTrack, init);

            // Offer
            MediaConstraints constraints = new MediaConstraints();
            constraints.mandatory.add(new MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"));
            constraints.mandatory.add(new MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"));

            peerConnection.createOffer(new SdpObserver() {
                @Override public void onCreateSuccess(SessionDescription sdp) {
                    Log.d(TAG, "Offer Created");
                    peerConnection.setLocalDescription(new SdpObserver() {
                        @Override public void onSetSuccess() {
                            JSObject ret = new JSObject();
                            ret.put("type", sdp.type.canonicalForm());
                            ret.put("sdp", sdp.description);
                            ScreenSharePlugin.sendEventToJS("onOfferGenerated", ret);
                        }
                        @Override public void onSetFailure(String s) { Log.e(TAG, "SetLocal Fail: " + s); }
                        @Override public void onCreateSuccess(SessionDescription s) {}
                        @Override public void onCreateFailure(String s) {}
                    }, sdp);
                }
                @Override public void onCreateFailure(String s) { Log.e(TAG, "Offer Fail: " + s); }
                @Override public void onSetFailure(String s) {}
                @Override public void onSetSuccess() {}
            }, constraints);

        } catch (Exception e) {
            Log.e(TAG, "CRASH: " + e.getMessage());
            e.printStackTrace();
            stopSelf();
        }
    }

    private void setRemoteDescription(String sdp) {
        if (peerConnection == null) return;
        SessionDescription answer = new SessionDescription(SessionDescription.Type.ANSWER, sdp);
        peerConnection.setRemoteDescription(new SdpObserver() {
            @Override public void onSetSuccess() { Log.d(TAG, "RemoteDesc Set OK"); }
            @Override public void onSetFailure(String s) { Log.e(TAG, "RemoteDesc Fail: " + s); }
            @Override public void onCreateSuccess(SessionDescription s) {}
            @Override public void onCreateFailure(String s) {}
        }, answer);
    }

    private void addIceCandidate(String mid, int idx, String sdp) {
        if (peerConnection != null) {
            peerConnection.addIceCandidate(new IceCandidate(mid, idx, sdp));
        }
    }

    private void stopStream() {
        try {
            if (capturer != null) { capturer.stopCapture(); capturer.dispose(); capturer = null; }
            if (videoSource != null) { videoSource.dispose(); videoSource = null; }
            if (peerConnection != null) { peerConnection.close(); peerConnection = null; }
            if (eglBase != null) { eglBase.release(); eglBase = null; }
            if (factory != null) { factory.dispose(); factory = null; }
        } catch (Exception e) { e.printStackTrace(); }
        
        stopForeground(true);
        stopSelf();
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null && manager.getNotificationChannel(CHANNEL_ID) == null) {
                NotificationChannel chan = new NotificationChannel(CHANNEL_ID, "ScreenShare", NotificationManager.IMPORTANCE_HIGH);
                chan.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
                manager.createNotificationChannel(chan);
            }
        }
    }
    
    @Override public IBinder onBind(Intent intent) { return null; }
}