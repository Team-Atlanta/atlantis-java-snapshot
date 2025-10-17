package sample;

public class BugOne {
    public void bug(byte[] data) throws Throwable {
        String[] cmds = new String(data).split("\0");
        new ProcessBuilder(cmds).start();
    }

    public void bug2(byte[] data) throws Throwable {
        if (data.length != 10) {
            return;
        }

        String[] cmds = new String(data).split("\0");
        new ProcessBuilder(cmds).start();
    }

    public void bug3(byte[] data) throws Throwable {
        String[] cmds = new String(data).split("\0");
        if (cmds.length == 1) Class.forName(cmds[0]); else if (cmds.length == 2) Class.forName(cmds[1]);
    }

    public void bug4(byte[] data) throws Throwable {
        String[] cmds = new String(data).split("\0");
        if (cmds.length > 0) {
            Class.forName(
                cmds[0]
            );
        }
    }
}
