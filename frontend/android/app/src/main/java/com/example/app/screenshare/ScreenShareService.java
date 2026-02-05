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
import android.media.projection.MediaProjection; 

import com.getcapacitor.JSObject;

import org.webrtc.*;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ScreenShareService extends Service {
    
    public static final String CHANNEL_ID = "ScreenShare_Service_V10";
    public static final int NOTIFICATION_ID = 999;
    private static final String TAG = "ScreenShareService";

    private PeerConnectionFactory factory;
    private PeerConnection peerConnection;
    private EglBase eglBase;
    private VideoSource videoSource;
    private ScreenCapturerAndroid capturer;
    private SurfaceTextureHelper textureHelper;
    private MediaProjection mediaProjection;
    
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    public void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null || intent.getAction() == null) return START_NOT_STICKY;

        String action = intent.getAction();
        Log.d(TAG, "onStartCommand Action: " + action);

        if ("START".equals(action)) {
            startForegroundNotification();
            
            int resultCode = intent.getIntExtra("RESULT_CODE", 0);
            Intent data = intent.getParcelableExtra("DATA");

            if (resultCode != 0 && data != null) {
                executor.execute(() -> initWebRTC(data));
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
            stopStream();
        }

        return START_STICKY;
    }

    private void startForegroundNotification() {
        int iconResId = android.R.drawable.ic_dialog_info;
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Демонстрация экрана")
                .setContentText("Идет трансляция...")
                .setSmallIcon(iconResId)
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setOngoing(true);

        if (Build.VERSION.SDK_INT >= 31) {
            builder.setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE);
        }

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

    private void initWebRTC(Intent data) {
        try {
            Log.d(TAG, "Initializing WebRTC inside Service...");
            Context ctx = getApplicationContext();
            
            PeerConnectionFactory.initialize(
                PeerConnectionFactory.InitializationOptions.builder(ctx).createInitializationOptions()
            );
            
            eglBase = EglBase.create();
            
            factory = 
                PeerConnectionFactory.builder()
                    .setVideoEncoderFactory(
                        new DefaultVideoEncoderFactory(eglBase.getEglBaseContext(), false, false)
                    )
                    .setVideoDecoderFactory(
                        new DefaultVideoDecoderFactory(eglBase.getEglBaseContext())
                    )
                    .setAudioDeviceModule(null) // 🔥 ВАЖНО
                    .createPeerConnectionFactory();

            List<PeerConnection.IceServer> iceServers = new ArrayList<>();
            iceServers.add(PeerConnection.IceServer.builder("stun:nex2ilo.com:3478").createIceServer());
            iceServers.add(PeerConnection.IceServer.builder("turn:nex2ilo.com:3478")
                .setUsername("kazgirls").setPassword("9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN").createIceServer());
            iceServers.add(PeerConnection.IceServer.builder("turns:nex2ilo.com:5349")
                 .setUsername("kazgirls").setPassword("9HeIgkJxNiCi0z9mPxho3TRQS5kVTmFN").createIceServer());

            PeerConnection.RTCConfiguration rtcConfig = new PeerConnection.RTCConfiguration(iceServers);
            rtcConfig.sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN;

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

            MediaProjectionManager mpm =
                (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);

            mediaProjection = mpm.getMediaProjection(Activity.RESULT_OK, data);

            mediaProjection.registerCallback(new MediaProjection.Callback() {
                @Override
                public void onStop() {
                    Log.e(TAG, "MediaProjection stopped by system");
                    stopStream();
                }
            }, null);

            // ВОТ ЗДЕСЬ БЫЛА ОШИБКА БЕЗ ИМПОРТА
            capturer = new ScreenCapturerAndroid(data, new MediaProjection.Callback() {
                @Override public void onStop() { Log.e(TAG, "System stopped projection"); stopStream(); }
            });

            textureHelper = SurfaceTextureHelper.create("ScreenCaptureThread", eglBase.getEglBaseContext());
            videoSource = factory.createVideoSource(true);
            capturer.initialize(textureHelper, ctx, videoSource.getCapturerObserver());

            Log.d(TAG, "Start Capture 720x1280...");
            DisplayMetrics metrics = ctx.getResources().getDisplayMetrics();
            int width = metrics.widthPixels;
            int height = metrics.heightPixels;

            capturer.startCapture(width, height, 30);

            VideoTrack videoTrack = factory.createVideoTrack("SCREEN_TRACK", videoSource);
            RtpTransceiver transceiver =
                peerConnection.addTransceiver(
                    videoTrack,
                    new RtpTransceiver.RtpTransceiverInit(
                    RtpTransceiver.RtpTransceiverDirection.SEND_ONLY
                    )
                );

            MediaConstraints constraints = new MediaConstraints();
            constraints.mandatory.add(new MediaConstraints.KeyValuePair("OfferToReceiveVideo", "true"));

            peerConnection.createOffer(new SdpObserver() {
                @Override public void onCreateSuccess(SessionDescription sdp) {
                    Log.d(TAG, "Offer Created!");
                    peerConnection.setLocalDescription(this, sdp);
                    
                    JSObject ret = new JSObject();
                    ret.put("type", sdp.type.canonicalForm());
                    ret.put("sdp", sdp.description);
                    ScreenSharePlugin.sendEventToJS("onOfferGenerated", ret);
                }
                @Override public void onCreateFailure(String s) { Log.e(TAG, "Offer Fail: " + s); }
                @Override public void onSetFailure(String s) {}
                @Override public void onSetSuccess() {}
            }, constraints);

        } catch (Exception e) {
            Log.e(TAG, "WebRTC Crash: " + e.getMessage());
            e.printStackTrace();
            stopSelf();
        }
    }

    private void setRemoteDescription(String sdp) {
        if (peerConnection == null) return;
        SessionDescription answer = new SessionDescription(SessionDescription.Type.ANSWER, sdp);
        peerConnection.setRemoteDescription(new SdpObserver() {
            @Override public void onSetSuccess() { Log.d(TAG, "Remote Set OK"); }
            @Override public void onSetFailure(String s) { Log.e(TAG, "Remote Set Fail: " + s); }
            @Override public void onCreateSuccess(SessionDescription sdp) {}
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
        } catch (Exception e) {}
        stopForeground(true);
        stopSelf();

        if (mediaProjection != null) {
            mediaProjection.stop();
            mediaProjection = null;
        }
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