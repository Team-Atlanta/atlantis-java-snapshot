import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;

/**
 *
 *  ★ Memory layout *
 *    Header(8B) : <item_size:uint32><item_num:uint32>   (Little-Endian)
 *    Item[n]    : <data_len:uint32><payload Bytes …>
 *
 */
public class SeedShmemPoolConsumer implements AutoCloseable {

    private static final int HEADER_SIZE = 8;        
    private static final int LEN_FIELD_SIZE = 4;     

    private final int itemSize;          
    private final int itemNum;           
    private final MappedByteBuffer buf;  
    private final FileChannel channel;   

    /**
     * @param shmName /dev/shm/<shmName>
     */
    public SeedShmemPoolConsumer(String shmName) throws IOException {

        Path shmPath = Paths.get("/dev/shm", shmName);

        this.channel = FileChannel.open(shmPath, StandardOpenOption.READ);
        long fileSize = channel.size();

        this.buf = channel.map(FileChannel.MapMode.READ_ONLY, 0, fileSize);
        this.buf.order(ByteOrder.LITTLE_ENDIAN);

        this.itemSize = buf.getInt(0);    // offset = 0
        this.itemNum  = buf.getInt(4);    // offset = 4

        long expect = HEADER_SIZE + (long) itemSize * itemNum;
        if (expect != fileSize) {
            throw new IllegalStateException(
                    "Shared memory size mismatch, expect=" + expect + ", real=" + fileSize);
        }
    }

    private int itemOffset(int idx) {
        if (idx < 0 || idx >= itemNum) throw new IndexOutOfBoundsException("idx out of range");
        return HEADER_SIZE + idx * itemSize;
    }

    /**
     * Read the payload of the specified seedId.
     * @return null if data_len == 0; otherwise, return the copied byte array.
     */
    public byte[] getSeedContent(int seedId) {
        if (seedId < 0 || seedId >= itemNum) return null;

        int off = itemOffset(seedId);

        int len = buf.getInt(off);     // data_len
        if (len <= 0 || len > itemSize - LEN_FIELD_SIZE) {
	    // empty or broken data
            return null;
        }

        byte[] data = new byte[len];
        int payloadStart = off + LEN_FIELD_SIZE;
        for (int i = 0; i < len; i++) {
            data[i] = buf.get(payloadStart + i);
        }
        return data;
    }

    public int getItemNum()  { return itemNum; }
    public int getItemSize() { return itemSize; }

    @Override
    public void close() throws IOException {
        channel.close();
    }
}
