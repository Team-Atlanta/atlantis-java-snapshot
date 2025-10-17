package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.espresso.EspressoLanguage;
import com.oracle.truffle.espresso.classfile.JavaKind;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.meta.Meta;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.oracle.truffle.espresso.descriptors.*;
import com.oracle.truffle.espresso.vm.InterpreterToVM;
import com.oracle.truffle.espresso.vm.UnsafeAccess;
import com.oracle.truffle.espresso.impl.*;
import java.lang.reflect.Array;
import sun.misc.Unsafe;
import java.nio.file.Path;
import java.util.*;

public class FileIOHook {
    public static long getEOF(StaticObject fdObj, boolean isInputStream) {
        return getOffset(fdObj, isInputStream, true);
    }

    public static long getOffset(StaticObject fdObj, boolean isInputStream) {
        return getOffset(fdObj, isInputStream, false);
    }

    public static long getOffset(StaticObject fdObj, boolean isInputStream, boolean getEOF) {
        try {
            if (StaticObject.isNull(fdObj)) {
                if (Logger.compileLog) {
                    synchronized (Z3Helper.getInstance()) {
                        Logger.WARNING("[FileIOHook] Got null in getOffset(" + fdObj + ", " + isInputStream + ", " + getEOF + ")");
                    }
                }
                return -1;
            }
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("[FileIOHook] getOffset(" + fdObj + ", " + isInputStream + ", " + getEOF + ")");
                }
            }
            Meta meta = fdObj.getKlass().getMeta();
            StaticObject fileChannel;
            if (isInputStream) {
                StaticObject fileInputStream = meta.java_io_FileInputStream.allocateInstance();
                meta.java_io_FileInputStream_init.invokeDirectSpecial(fileInputStream, fdObj);
                fileChannel = (StaticObject) meta.java_io_FileInputStream_getChannel.invokeDirect(fileInputStream);
            } else {
                StaticObject fileOutputStream = meta.java_io_FileOutputStream.allocateInstance();
                meta.java_io_FileOutputStream_init.invokeDirectSpecial(fileOutputStream, fdObj);
                fileChannel = (StaticObject) meta.java_io_FileOutputStream_getChannel.invokeDirect(fileOutputStream);
            }
            if (!getEOF) {
                return (Long) meta.sun_nio_ch_FileChannelImpl_position.invokeDirect(fileChannel);
            } else {
                return (Long) meta.sun_nio_ch_FileChannelImpl_size.invokeDirect(fileChannel);
            }
        } catch (Exception e) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.WARNING("[FileIOHook] Failed to getOffset(" + fdObj + ", " + isInputStream + ", " + getEOF + ") " + e);
                }
            }
            return -1;
        }
    }

    public static void wrapInvokeMethod(String className,
                                        String methodName,
                                        Object[] args,
                                        String signature) {
        switch (methodName) {
            case "writeBytes":
                if (Logger.compileLog) {
                    Logger.DEBUG("[FileIOHook] InvokeHook " + methodName + signature);
                }
                if (signature.equals("([BIIZ)V") || signature.equals("([BII)V")) {
                    long fileOffset;
                    ConcolicObjectImpl thisObj = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                    ConcolicObjectImpl fdObj = (ConcolicObjectImpl) thisObj.getOrCreateField(0);
                    int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                    if (fd < 3) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                        }
                        return;
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("[FileIOHook] getting position of fd: " + fd);
                    }
                    if ((Boolean) ConcolicHelper.toConcrete(args[4])) {
                        fileOffset = getEOF(fdObj.getConcreteObject(), false);
                    } else {
                        fileOffset = getOffset(fdObj.getConcreteObject(), false);
                    }
                    if (fileOffset >= 0) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] put position of fd: " + fd + "," + fileOffset);
                        }
                        ConcolicHelper.fdOffsetMap.put(fd, fileOffset);
                    } else {
                        if (Logger.compileLog) {
                            Logger.WARNING("[FileIOHook] wrong position of fd: " + fd + "," + fileOffset);
                        }
                    }
                }
                break;
        }
    }

    public static Object wrapMethod(String className,
                                    String methodName,
                                    Object[] args,
                                    String signature,
                                    Object returnedObject) {
        if (Logger.compileLog) {
            Logger.DEBUG("[FileIOHook] " + methodName + signature);
        }
        switch (methodName) {
            case "<init>": {
                if (className.equals("java/io/FileInputStream") || className.equals("java/io/FileOutputStream")
                        || className.equals("java/io/RandomAccessFile")) {
                    try {
                        ConcolicObjectImpl thisObj = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                        ConcolicObjectImpl fdObj = (ConcolicObjectImpl) thisObj.getOrCreateField(0);
                        int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                        if (fd < 3) {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                            }
                            return returnedObject;
                        }
                        ConcolicObjectImpl pathObj = className.equals("java/io/FileInputStream")
                                ? (ConcolicObjectImpl) thisObj.getOrCreateField(1)
                                : (ConcolicObjectImpl) thisObj.getOrCreateField(2);
                        String path = Path.of(Meta.toHostStringStatic(pathObj.getConcreteObject())).toRealPath().toString();
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] open fd: " + fd + ", " + path);
                        }
                        ConcolicHelper.fdPathMap.put(fd, path);
                    } catch (Exception e) {
                        if (Logger.compileLog) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.WARNING("[FileIOHook] Failed open: " + e);
                            }
                        }
                    }
                }
                break;
            }
            case "open": {
                if (signature.equals("(Lsun/nio/fs/UnixPath;II)I")) {
                    try {
                        int fd = (Integer) ConcolicHelper.toConcrete(returnedObject);
                        if (fd < 3) {
                            if (Logger.compileLog) {
                                Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                            }
                            return returnedObject;
                        }
                        ConcolicObjectImpl unixPath = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                        StaticObject unixPathSO = unixPath.getConcreteObject();
                        if (Logger.compileLog) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.DEBUG("[FileIOHook] invoking toRealPath: " + unixPath);
                            }
                        }
                        Meta meta = unixPathSO.getKlass().getMeta();
                        StaticObject emptyArrSO = StaticObject.wrap(StaticObject.EMPTY_ARRAY, meta);
                        StaticObject realPath = (StaticObject) meta.sun_nio_fs_UnixPath_toRealPath.invokeDirect(unixPathSO, emptyArrSO);
                        StaticObject realPathStr = (StaticObject) meta.sun_nio_fs_UnixPath_toString.invokeDirect(realPath);
                        String path = Meta.toHostStringStatic(realPathStr);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] open fd: " + fd + ", " + path);
                        }
                        ConcolicHelper.fdPathMap.put(fd, path);
                    } catch (Exception e) {
                        if (Logger.compileLog) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.WARNING("[FileIOHook] Failed open: " + e);
                            }
                        }
                    }
                }
                break;
            }
            case "writeBytes": {
                if (signature.equals("([BIIZ)V")) {
                    ConcolicObjectImpl fos = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                    ConcolicObjectImpl fdObj = (ConcolicObjectImpl) fos.getOrCreateField(0);
                    int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                    if (fd < 3) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                        }
                        return returnedObject;
                    }
                    if (!ConcolicHelper.fdPathMap.containsKey(fd)) {
                        if (Logger.compileLog) {
                            Logger.WARNING("[FileIOHook] Not found fd: " + fd);
                        }
                        return returnedObject;
                    }
                    String path = ConcolicHelper.fdPathMap.get(fd);
                    if (Logger.compileLog) {
                        Logger.DEBUG("[FileIOHook] writeBytes fd: " + fd + ", " + path);
                    }
                    int arrIndex = (Integer) ConcolicHelper.toConcrete(args[2]);
                    Long fileOffset = ConcolicHelper.fdOffsetMap.get(fd);
                    if (fileOffset == null || fileOffset == -1) {
                        if (Logger.compileLog) {
                            Logger.WARNING("[FileIOHook] Failed writeBytes: " + fd);
                        }
                        return returnedObject;
                    } else if (Logger.compileLog) {
                        Logger.DEBUG("[FileIOHook] writeBytes fd: " + fd + ", fileOffset: " + fileOffset + ", arrIndex: " + arrIndex);
                    }
                    long length = getOffset(fdObj.getConcreteObject(), false) - fileOffset;
                    if (!ConcolicHelper.fileContentMap.containsKey(path)) {
                        ConcolicHelper.fileContentMap.put(path, new HashMap<Long, ConcolicValueWrapper<?>>());
                    }
                    Map<Long, ConcolicValueWrapper<?>> offsetConcolicMap = ConcolicHelper.fileContentMap.get(path);
                    ConcolicObjectImpl ba = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[1]);
                    for (int i = 0; i < length && i < ba.getConcreteSize(); i++) {
                        long curFileOffset = fileOffset + i;
                        int curArrIndex = arrIndex + i;
                        if (curFileOffset < 0 || curArrIndex < 0) {
                            if (Logger.compileLog) {
                                Logger.WARNING("[FileIOHook] writeBytes failed: " + fd + ", " + path);
                            }
                            return returnedObject;
                        }
                        // obj -> file
                        ConcolicByte concolic = (ConcolicByte) ba.getOrCreateField(curArrIndex);
                        ConcolicByte b = new ConcolicByte();
                        b.setValueWithConstraints(concolic.getConcreteValue(), concolic.getExpr());
                        offsetConcolicMap.put(curFileOffset, b);
                        if (Logger.compileLog) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.DEBUG("[FileIOHook] obj -> file: " + offsetConcolicMap.get(curFileOffset));
                            }
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("[FileIOHook] writeBytes succeed: " + length);
                    }
                }
                break;
            }
            case "write0": {
                if (signature.equals("(Ljava/io/FileDescriptor;JI)I")) {
                    ConcolicObjectImpl fdObj = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                    int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                    if (fd < 3) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                        }
                        return returnedObject;
                    }
                    if (ConcolicHelper.fdPathMap.containsKey(fd)) {
                        String path = ConcolicHelper.fdPathMap.get(fd);
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] write0 fd: " + fd + ", " + path);
                        }
                        if (!ConcolicHelper.fileContentMap.containsKey(path)) {
                            ConcolicHelper.fileContentMap.put(path, new HashMap<Long, ConcolicValueWrapper<?>>());
                        }
                        int length = (Integer) ConcolicHelper.toConcrete(returnedObject);
                        long heapOffset = (Long) ConcolicHelper.toConcrete(args[1]);
                        long fileOffset = getOffset(fdObj.getConcreteObject(), false) - (long) length;
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] write0 fd: " + fd + ", fileOffset: " + fileOffset + ", heapOffset: " + heapOffset);
                        }
                        Map<Long, ConcolicValueWrapper<?>> offsetConcolicMap = ConcolicHelper.fileContentMap.get(path);
                        for (int i = 0; i < length; i++) {
                            long curFileOffset = fileOffset + i;
                            long curHeapOffset = heapOffset + i;
                            if (curFileOffset < 0 || curHeapOffset < 0 || !ConcolicHelper.allocMap.containsKey(curHeapOffset)) {
                                if (Logger.compileLog) {
                                    Logger.WARNING("[FileIOHook] write0 failed: " + fd + ", " + path);
                                }
                                return returnedObject;
                            }
                            ConcolicByte concolic = (ConcolicByte) ConcolicHelper.allocMap.get(curHeapOffset);
                            byte concrete = UnsafeHook.UNSAFE.getByte(curHeapOffset);
                            if (concolic.getConcreteValue() != concrete) {
                                if (Logger.compileLog) {
                                    synchronized (Z3Helper.getInstance()) {
                                        Logger.WARNING("[FileIOHook] write0 Mismatch concolic: " + concolic + ", concrete: " + concrete);
                                    }
                                }
                                return returnedObject;
                            }
                            // heap -> file
                            ConcolicByte b = new ConcolicByte();
                            b.setValueWithConstraints(concrete, concolic.getExpr());
                            offsetConcolicMap.put(curFileOffset, b);
                            if (Logger.compileLog) {
                                synchronized (Z3Helper.getInstance()) {
                                    Logger.DEBUG("[FileIOHook] heap -> file: " + offsetConcolicMap.get(curFileOffset));
                                }
                            }
                        }
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] write0 succeed: " + length);
                        }
                    }
                }
                break;
            }
            case "readBytes": {
                if (signature.equals("([BII)I")) {
                    ConcolicObjectImpl fis = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                    ConcolicObjectImpl fdObj = (ConcolicObjectImpl) fis.getOrCreateField(0);
                    int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                    if (fd < 3) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                        }
                        return returnedObject;
                    }
                    if (!ConcolicHelper.fdPathMap.containsKey(fd)) {
                        if (Logger.compileLog) {
                            Logger.WARNING("[FileIOHook] Not found fd: " + fd);
                        }
                        return returnedObject;
                    }
                    String path = ConcolicHelper.fdPathMap.get(fd);
                    if (!ConcolicHelper.fileContentMap.containsKey(path)) {
                        if (Logger.compileLog) {
                            Logger.WARNING("[FileIOHook] not found: " + path);
                        }
                        return returnedObject;
                    } else if (Logger.compileLog) {
                        Logger.DEBUG("[FileIOHook] readBytes fd: " + fd + ", " + path);
                    }
                    int length = (Integer) ConcolicHelper.toConcrete(returnedObject);
                    long fileOffset = getOffset(fdObj.getConcreteObject(), false) - (long) length;
                    int arrIndex = (Integer) ConcolicHelper.toConcrete(args[2]);
                    Map<Long, ConcolicValueWrapper<?>> offsetConcolicMap = ConcolicHelper.fileContentMap.get(path);
                    ConcolicObjectImpl ba = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[1]);
                    for (int i = 0; i < length && i < ba.getConcreteSize(); i++) {
                        long curFileOffset = fileOffset + i;
                        int curArrIndex = arrIndex + i;
                        if (curFileOffset < 0 || curArrIndex < 0) {
                            if (Logger.compileLog) {
                                Logger.WARNING("[FileIOHook] readBytes failed: " + fd + ", " + path);
                            }
                            return returnedObject;
                        }
                        // file -> obj
                        ConcolicByte concolicObj = (ConcolicByte) ba.getOrCreateField(curArrIndex);
                        ConcolicByte concolicFile = (ConcolicByte) offsetConcolicMap.get(curFileOffset);

                        Klass klass = ba.getConcreteObject().getKlass();
                        InterpreterToVM interpreterToVM = klass.getContext().getInterpreterToVM();
                        EspressoLanguage language = klass.getMeta().getLanguage();
                        byte concrete = interpreterToVM.getArrayByte(language, curArrIndex, ba.getConcreteObject());
                        if (concolicFile.getConcreteValue() != concrete) {
                            if (Logger.compileLog) {
                                synchronized (Z3Helper.getInstance()) {
                                    Logger.WARNING("[FileIOHook] readBytes Mismatch concolic: " + concolicFile + ", concrete: " + concrete);
                                }
                            }
                            return returnedObject;
                        }
                        concolicObj.setValueWithConstraints(concrete, concolicFile.getExpr());
                        if (Logger.compileLog) {
                            synchronized (Z3Helper.getInstance()) {
                                Logger.DEBUG("[FileIOHook] file -> obj: " + concolicObj);
                            }
                        }
                    }
                    if (Logger.compileLog) {
                        Logger.DEBUG("[FileIOHook] readBytes succeed: " + length);
                    }
                }
                break;
            }
            case "read0": {
                if (signature.equals("(Ljava/io/FileDescriptor;JI)I")) {
                    ConcolicObjectImpl fdObj = (ConcolicObjectImpl) ConcolicHelper.toConcolic(args[0]);
                    int fd = (int) ConcolicHelper.toConcrete(fdObj.getOrCreateField(0));
                    if (fd < 3) {
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] Skip stdin/stdout/error: " + fd);
                        }
                        return returnedObject;
                    }
                    if (ConcolicHelper.fdPathMap.containsKey(fd)) {
                        String path = ConcolicHelper.fdPathMap.get(fd);
                        if (!ConcolicHelper.fileContentMap.containsKey(path)) {
                            if (Logger.compileLog) {
                                Logger.WARNING("[FileIOHook] read0 failed: " + fd + ", " + path);
                            }
                            return returnedObject;
                        }
                        int length = (Integer) ConcolicHelper.toConcrete(returnedObject);
                        long heapOffset = (Long) ConcolicHelper.toConcrete(args[1]);
                        long fileOffset = getOffset(fdObj.getConcreteObject(), true) - (long) length;
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] read0 fd: " + fd + ", fileOffset: " + fileOffset + ", heapOffset: " + heapOffset);
                        }
                        Map<Long, ConcolicValueWrapper<?>> fileOffsetConcolicMap = ConcolicHelper.fileContentMap.get(path);
                        for (int i = 0; i < length; i++) {
                            long curFileOffset = fileOffset + i;
                            long curHeapOffset = heapOffset + i;
                            if (curFileOffset < 0 || curHeapOffset < 0
                                    || fileOffsetConcolicMap == null || !fileOffsetConcolicMap.containsKey(curFileOffset)) {
                                if (Logger.compileLog) {
                                    Logger.WARNING("[FileIOHook] read0 failed: " + fd + ", " + path);
                                }
                                return returnedObject;
                            }
                            // file -> heap
                            ConcolicByte concolic = (ConcolicByte) fileOffsetConcolicMap.get(curFileOffset);
                            byte concrete = UnsafeHook.UNSAFE.getByte(curHeapOffset);
                            if (concolic.getConcreteValue() != concrete) {
                                if (Logger.compileLog) {
                                    synchronized (Z3Helper.getInstance()) {
                                        Logger.WARNING("[FileIOHook] read0 Mismatch concolic: " + concolic + ", concrete: " + concrete);
                                    }
                                }
                                return returnedObject;
                            }
                            ConcolicByte b = new ConcolicByte();
                            b.setValueWithConstraints(concrete, concolic.getExpr());
                            ConcolicHelper.allocMap.put(curHeapOffset, b);
                            if (Logger.compileLog) {
                                synchronized (Z3Helper.getInstance()) {
                                    Logger.DEBUG("[FileIOHook] file -> heap: " + ConcolicHelper.allocMap.get(curHeapOffset));
                                }
                            }
                        }
                        if (Logger.compileLog) {
                            Logger.DEBUG("[FileIOHook] read0 succeed: " + length);
                        }
                    }
                }
                break;
            }
        }
        return returnedObject;
    }
}
