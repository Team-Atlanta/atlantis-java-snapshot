import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Formatter;

public class ShmConsumer {

    private static String sha256Hex(byte[] data) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] digest   = md.digest(data);
        Formatter f = new Formatter();
        for (byte b : digest) f.format("%02x", b);
        return f.toString();
    }

    private static void hexdump(byte[] data) {
        final int perLine = 16;
        for (int i = 0; i < data.length; i += perLine) {
            System.out.printf("%08x  ", i);
            for (int j = 0; j < perLine; ++j) {
                if (i + j < data.length)
                    System.out.printf("%02x ", data[i + j]);
                else
                    System.out.print("   ");
                if (j == 7) System.out.print(" ");
            }
            System.out.print(" |");
            for (int j = 0; j < perLine; ++j) {
                if (i + j < data.length) {
                    byte b = data[i + j];
                    char c = (b >= 32 && b <= 126) ? (char) b : '.';
                    System.out.print(c);
                } else {
                    System.out.print(' ');
                }
            }
            System.out.println('|');
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: java ShmConsumer <shm_name> <seed_id>");
            return;
        }
        String shmName = args[0];
        int    seedId  = Integer.parseInt(args[1]);

        try (SeedShmemPoolConsumer c = new SeedShmemPoolConsumer(shmName)) {
            byte[] data = c.getSeedContent(seedId);
            if (data == null) {
                System.out.println("slot empty or invalid");
                return;
            }
            System.out.println("length = " + data.length + " bytes");
            System.out.println("sha256 = " + sha256Hex(data));
            hexdump(data);
        }
    }
}
