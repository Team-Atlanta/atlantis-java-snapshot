package sample;
import java.io.IOException;

public class BugTwo {
    public void run(byte[] data) {
        _run(data);
    }

    void _run(byte[] data) {
        try {
            String[] cmds = new String(data).split("\0");
            new ProcessBuilder(cmds).start();
        } catch (IOException e) {}
    }
}
