package sample.one;

import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.util.Arrays;
import sample.BugOne;


public class SampleOne {
    public static void fuzzerTestOneInput(byte[] data) throws Throwable {
        new SampleOne().fuzz(data);
    }

    public void fuzz(byte[] data) throws Throwable {
        ByteBuffer buf = ByteBuffer.wrap(data);
        int picker = buf.getInt();
        int count = buf.getInt();
        if (count > 255)
            return;
        for (int i = 0; i < count; i++) {
            try {
                switch (picker) {
                    case 10:
                        new BugOne().bug(Arrays.copyOfRange(data, 8, data.length));
                        break;
                    case 11:
                        new BugOne().bug2(Arrays.copyOfRange(data, 8, data.length));
                        break;
                    case 12:
                        while (true) {}
                    case 13:
                        try {
                            Class<?> cls = Class.forName("Sample.BugTwo");
                            Object obj = cls.getDeclaredConstructor().newInstance();
                            Method m = cls.getDeclaredMethod("run", byte[].class);
                            m.setAccessible(true);
                            m.invoke(Arrays.copyOfRange(data, 8, data.length));
                        } catch (Exception e) {}
                        break;
                    default:
                        throw new Exception("unsupported method picker");
                }
            } catch (Exception e) {
                continue;
            }
        }
    }
}
