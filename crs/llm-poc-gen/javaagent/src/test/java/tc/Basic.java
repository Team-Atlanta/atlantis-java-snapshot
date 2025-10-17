package tc;

public class Basic {
    static int g = 0;
    public static void main(String[] args) {
        if (args.length < 1) {
            return;
        }

        String a = args[0];
        if (a.startsWith("A")) {
            g = 1;
            if (a.equals("ABC")) {
                g = 2;
            }
        } else {
            g = 3;
        }
    }
}
