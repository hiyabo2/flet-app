package by.bytebloom.down_free;

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

        createNotificationChannel();
        startForeground(1, buildNotification("App ejecutándose en segundo plano"));
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Foreground Service",
                NotificationManager.IMPORTANCE_HIGH  // Asegura que sea visible
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification buildNotification(String message) {
        return new Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Down Free")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .setPriority(Notification.PRIORITY_HIGH)  // IMPORTANTE
            .build();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "🔄 Manteniendo la app activa en segundo plano...");
        startForeground(1, buildNotification("Servicio aún en ejecución"));
        return START_STICKY;  // Mantiene el servicio activo
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
