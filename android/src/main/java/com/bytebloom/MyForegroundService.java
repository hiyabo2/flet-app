package by.bytebloom;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;

public class MyForegroundService extends Service {
    private static final String TAG = "MyForegroundService";
    private static final String CHANNEL_ID = "ForegroundServiceChannel";

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "🚀 Servicio en segundo plano iniciado...");

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Foreground Service",
                NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
            Notification notification = new Notification.Builder(this, CHANNEL_ID)
                .setContentTitle("App ejecutándose en segundo plano")
                .setContentText("Presiona aquí para volver a la app")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setOngoing(true)
                .build();
            startForeground(1, notification);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "🔄 Manteniendo la app activa en segundo plano...");
        return START_STICKY;  // Hace que el servicio se reinicie si el sistema lo mata
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
