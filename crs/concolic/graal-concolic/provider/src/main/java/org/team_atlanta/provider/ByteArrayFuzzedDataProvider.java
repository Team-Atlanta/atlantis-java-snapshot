package org.team_atlanta.provider;

import java.util.*;
import java.nio.*;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class ByteArrayFuzzedDataProvider implements FuzzedDataProvider {
    public byte[] byteStream;
    public int currentIndex;
    public int lastIndex;

    // constructor
    public ByteArrayFuzzedDataProvider(byte[] stream) {
        this.byteStream = stream;
        currentIndex = 0;
        lastIndex = 0;
    }

    public int getRemainingLength() {
        int remainingLength = byteStream.length - currentIndex;
        return remainingLength;
    }

    public int normalizeMaxLength(int maxLength, int typeSize) {
        int remainingLength = (byteStream.length - currentIndex) / typeSize;
        if (maxLength <= remainingLength) {
            return maxLength;
        } else {
            return remainingLength;
        }
    }

    @Override
    public boolean consumeBoolean() {
        lastIndex = currentIndex;
        currentIndex += 1;
        byte byteValue = this.byteStream[lastIndex];
        if (byteValue == 1) {
            return true;    // TODO: need to link this value to boolean, can be done in ConcolicBoolean
        } else {
            return false;
        }
    }

    @Override
    public boolean[] consumeBooleans(int maxLength) {
        int totalLength = normalizeMaxLength(maxLength, 1);
        lastIndex = currentIndex;
        currentIndex += totalLength;
        boolean[] toBeReturned = new boolean[totalLength];
        for (int i=0; i < totalLength; ++i) {
            if (this.byteStream[lastIndex+i] == 1) {
                toBeReturned[i] = true;
            } else {
                toBeReturned[i] = false;
            }
        }
        return toBeReturned;
    }

    @Override
    public byte consumeByte() {
        lastIndex = currentIndex;
        currentIndex += 1;
        return this.byteStream[lastIndex];
    }

    @Override
    public byte consumeByte(byte min, byte max) {
        return consumeByte();
    }

    @Override
    public byte[] consumeBytes(int maxLength) {
        int totalLength = normalizeMaxLength(maxLength, 1);
        lastIndex = currentIndex;
        currentIndex += totalLength;
        byte[] toBeReturned = new byte[totalLength];
        for (int i=0; i < totalLength; ++i) {
            toBeReturned[i] = this.byteStream[lastIndex+i];
        }
        return toBeReturned;
    }

    @Override
    public short consumeShort() {
        lastIndex = currentIndex;
        currentIndex += 2;
        short b0 = (short) this.byteStream[lastIndex];
        short b1 = (short) this.byteStream[lastIndex+1];
        short toBeReturned = (short) ((b0 << 8) | b1);
        return toBeReturned;
    }

    @Override
    public short consumeShort(short min, short max) {
        return consumeShort();
    }

    @Override
    public short[] consumeShorts(int maxLength) {
        int totalLength = normalizeMaxLength(maxLength, 2);
        short[] toBeReturned = new short[totalLength];
        for (int i=0; i<totalLength; ++i) {
            toBeReturned[i] = consumeShort();
        }
        return toBeReturned;
    }

    @Override
    public int consumeInt() {
        lastIndex = currentIndex;
        currentIndex += 4;
        int b0 = (int) this.byteStream[lastIndex];
        int b1 = (int) this.byteStream[lastIndex+1];
        int b2 = (int) this.byteStream[lastIndex+2];
        int b3 = (int) this.byteStream[lastIndex+3];
        int toBeReturned = (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
        return toBeReturned;
    }

    @Override
    public int consumeInt(int min, int max) {
        return consumeInt();
    }

    @Override
    public int[] consumeInts(int maxLength) {
        int totalLength = normalizeMaxLength(maxLength, 4);
        int[] toBeReturned = new int[totalLength];
        for (int i=0; i<totalLength; ++i) {
            toBeReturned[i] = consumeInt();
        }
        return toBeReturned;
    }

    @Override
    public long consumeLong() {
        lastIndex = currentIndex;
        currentIndex += 8;
        long b0 = (int) this.byteStream[lastIndex];
        long b1 = (int) this.byteStream[lastIndex+1];
        long b2 = (int) this.byteStream[lastIndex+2];
        long b3 = (int) this.byteStream[lastIndex+3];
        long b4 = (int) this.byteStream[lastIndex+4];
        long b5 = (int) this.byteStream[lastIndex+5];
        long b6 = (int) this.byteStream[lastIndex+6];
        long b7 = (int) this.byteStream[lastIndex+7];
        long toBeReturned = (b0 << 56) | (b1 << 48) | (b2 << 40) | (b3 << 32);
        toBeReturned |= (b4 << 24) | (b5 << 16) | (b6 << 8) | b7;
        return toBeReturned;
    }

    @Override
    public long consumeLong(long min, long max) {
        return consumeLong();
    }

    @Override
    public long[] consumeLongs(int maxLength) {
        int totalLength = normalizeMaxLength(maxLength, 8);
        long[] toBeReturned = new long[totalLength];
        for (int i=0; i<totalLength; ++i) {
            toBeReturned[i] = consumeLong();
        }
        return toBeReturned;
    }

    @Override
    public float consumeFloat() {
        return 0.0f;
    }

    @Override
    public float consumeRegularFloat() {
        return 0.0f;
    }

    @Override
    public float consumeRegularFloat(float min, float max) {
        return consumeRegularFloat();
    }

    @Override
    public float consumeProbabilityFloat() {
        return 0.0f;
    }

    @Override
    public double consumeDouble() {
        return 0.0;
    }

    @Override
    public double consumeRegularDouble(double min, double max) {
        return consumeRegularDouble();
    }

    @Override
    public double consumeRegularDouble() {
        return 0.0;
    }

    @Override
    public double consumeProbabilityDouble() {
        return 0.0;
    }

    @Override
    public char consumeChar() {
        return "\0".charAt(0);
    }

    @Override
    public char consumeChar(char min, char max) {
        return consumeChar();
    }

    @Override
    public char consumeCharNoSurrogates() {
        return "\0".charAt(0);
    }

    @Override
    public String consumeAsciiString(int maxLength) {
        return consumeString(maxLength);
    }

    @Override
    public String consumeString(int maxLength) {
        int totalLength = normalizeMaxLength(maxLength, 1);
        lastIndex = currentIndex;
        currentIndex += totalLength;
        byte[] array = Arrays.copyOfRange(this.byteStream, lastIndex, currentIndex);
        return new String(array);
    }

    @Override
    public String consumeRemainingAsAsciiString() {
        return consumeRemainingAsString();
    }

    @Override
    public String consumeRemainingAsString() {
        return consumeString(remainingBytes());
    }

    @Override
    public byte[] consumeRemainingAsBytes() {
        lastIndex = currentIndex;
        currentIndex = remainingBytes();
        byte[] array = Arrays.copyOfRange(this.byteStream, lastIndex, currentIndex);
        return array;
    }

    @Override
    public int remainingBytes() {
        return byteStream.length - lastIndex;
    }

}
