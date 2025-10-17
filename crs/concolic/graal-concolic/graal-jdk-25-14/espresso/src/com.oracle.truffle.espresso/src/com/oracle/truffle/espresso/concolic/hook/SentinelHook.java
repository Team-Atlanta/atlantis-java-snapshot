package com.oracle.truffle.espresso.concolic.hook;

import com.oracle.truffle.api.concolic.*;
import com.oracle.truffle.api.interop.InteropLibrary;
import com.oracle.truffle.espresso.concolic.*;
import com.oracle.truffle.espresso.runtime.staticobject.StaticObject;
import com.microsoft.z3.*;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

public class SentinelHook {
    private static InteropLibrary interop = InteropLibrary.getFactory().createDispatched(3);

    // Note: Currently sanitizers using Jazzer.guideTowardsEquality() are not used
    public static void wrapMethod(String className,
                                  String methodName,
                                  Object[] args,
                                  String signature) {
        String classAndMethodName = className + "." + methodName;
        switch (classAndMethodName) {
            case "java/nio/file/Files.createDirectory":
            case "java/nio/file/Files.createDirectories":
            case "java/nio/file/Files.createFile":
            case "java/nio/file/Files.createTempDirectory":
            case "java/nio/file/Files.createTempFile":
            case "java/nio/file/Files.delete":
            case "java/nio/file/Files.deleteIfExists":
            case "java/nio/file/Files.lines":
            case "java/nio/file/Files.newByteChannel":
            case "java/nio/file/Files.newBufferedReader":
            case "java/nio/file/Files.newBufferedWriter":
            case "java/nio/file/Files.readString":
            case "java/nio/file/Files.readAllBytes":
            case "java/nio/file/Files.readAllLines":
            case "java/nio/file/Files.readSymbolicLink":
            case "java/nio/file/Files.write":
            case "java/nio/file/Files.writeString":
            case "java/nio/file/Files.newInputStream":
            case "java/nio/file/Files.newOutputStream":
            case "java/nio/file/probeContentType.open":
            case "java/nio/channels/FileChannel.open":
            case "java/nio/file/Files.copy":
            case "java/nio/file/Files.mismatch":
            case "java/nio/file/Files.move":
            case "java/io/FileReader.<init>":
            case "java/io/FileWriter.<init>":
            case "java/io/FileInputStream.<init>":
            case "java/io/FileOutputStream.<init>":
            case "java/util/Scanner.<init>":
                wrapFilePathTraversal(className, methodName, args, signature);
                break;
            case "java/lang/ProcessImpl.start":
            case "java/lang/ProcessBuilder.start":
                wrapOsCommandInjection(className, methodName, args, signature);
                break;
            case "java/lang/Class.forName":
            case "java/lang/ClassLoader.loadClass":
                wrapReflectiveCallToClass(className, methodName, args, signature);
                break;
            case "java/lang/Runtime.load":
            case "java/lang/Runtime.loadLibrary":
            case "java/lang/System.load":
            case "java/lang/System.loadLibrary":
            case "java/lang/System.mapLibraryName":
            case "java/lang/ClassLoader.findLibrary":
                wrapReflectiveCallToLibrary(className, methodName, args, signature);
                break;
            case "javax/xml/xpath/XPath.compile":
            case "javax/xml/xpath/XPath.evaluate":
            case "javax/xml/xpath/XPath.evaluateExpression":
                wrapXPathInjection(className, methodName, args, signature);
                break;
            case "java/net/URL.<init>":
            case "java/net/Socket.connect":
            case "java/net/SocketImpl.connect":
            case "java/net/SocksSocketImpl.connect":
            case "java/nio/channels/SocketChannel.connect":
            case "sun/nio/ch/SocketAdaptor.connect":
            case "jdk/internal/net/http/PlainHttpConnection.connect":
                wrapServerSideRequestForgery(className, methodName, args, signature);
                break;
            default:
                break;
        }
    }

    public static void injectOOM(ConcolicInt concolic, String identifier) {
        if (Logger.compileLog) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("[SENTINEL] injectOOM: " + identifier + " : " + concolic);
            }
        }
        if (!concolic.isSymbolic()) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("[SENTINEL] It's not symbolic: " + concolic);
                }
            }
            return;
        }
        ConcolicVariableInfo.oomExprMap.put((BitVecExpr) concolic.getExprWithInitInWidth(32), identifier);
        Logger.SOLVER("[SENTINEL] Added OOM Input: " + identifier);
    }

    public static void injectCMDI(ConcolicArrayObject ba) {
        String sentinel = "jazze";
        String name = "CMDI";
        if (ba.getConcreteSize() < sentinel.length()) {
            if (Logger.compileLog) {
                Logger.DEBUG("[SENTINEL] bytearray is shorter than injectSentinel(" + sentinel + ")");
            }
            return;
        } else if (ba.getConcreteSize() == sentinel.length()) {
            injectSentinel(ba, sentinel, name);
        } else {
            int offset = ba.getConcreteSize() - sentinel.length() - 1;
            injectSentinel(ba, "/" + sentinel, name, offset);
            injectSentinel(ba, "\\" + sentinel, name, offset);
        }
    }

    private static void injectSentinel(ConcolicArrayObject concolic, String sentinel, String name) {
        injectSentinel(concolic, sentinel, name, 0);
    }

    private static void injectSentinel(ConcolicArrayObject concolic, String sentinel, String name, int offset) {
        if (!concolic.isSymbolic()) {
            if (Logger.compileLog) {
                synchronized (Z3Helper.getInstance()) {
                    Logger.DEBUG("[SENTINEL] It's not symbolic: " + concolic);
                }
            }
            return;
        }
        if (concolic.getConcreteSize() < sentinel.length()) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("[SENTINEL] Too short length: " + concolic);
            }
            return;
        }
        if (Logger.compileLog) {
            synchronized (Z3Helper.getInstance()) {
                Logger.DEBUG("[SENTINEL] injectSentinel(" + sentinel + "): " + concolic);
            }
        }
        List<BoolExpr> conds = new ArrayList<>();
        for (int i = 0; i < sentinel.length() && i < concolic.getConcreteSize(); i++) {
            int fieldIdx = i + offset;
            ConcolicByte byte_ = (ConcolicByte) concolic.getOrCreateField(fieldIdx);
            if (byte_ == null || !byte_.isSymbolic()) {
                if (Logger.compileLog && byte_ != null) {
                    synchronized (Z3Helper.getInstance()) {
                        Logger.DEBUG("[SENTINEL] It's not symbolic byte[" + fieldIdx + "]: " + byte_);
                    }
                }
                continue;
            }
            conds.add(Z3Helper.mkEq(byte_.getExprWithInitInWidth(32), Z3Helper.mkBV(sentinel.charAt(i) & 0xff, 32)));
        }
        String identifier = "Sentinel-" + ConcolicVariableInfo.sentinelExprLists.size() + "-" + name;
        ConcolicVariableInfo.sentinelExprLists.add(conds);
        ConcolicVariableInfo.sentinelIdentifierList.add(identifier);
        Logger.SOLVER("[SENTINEL] Added sentinel: " + identifier);
    }

    private static void injectSentinelCond(List<BoolExpr> conds, String name) {
        String identifier = "Sentinel-" + ConcolicVariableInfo.sentinelExprLists.size() + "-" + name;
        ConcolicVariableInfo.sentinelExprLists.add(conds);
        ConcolicVariableInfo.sentinelIdentifierList.add(identifier);
        Logger.SOLVER("[SENTINEL] Added sentinel: " + identifier);
    }

    public static final String FILE_PATH_TARGET_KEY = "jazzer.file_path_traversal_target";
    public static final String DEFAULT_TARGET_STRING = "../jazzer-traversal";
    private static Path RELATIVE_TARGET;
    private static Path ABSOLUTE_TARGET;
    private static boolean IS_DISABLED = false;
    private static boolean IS_SET_UP = false;

    private static void setTargets(String targetPath) {
        Path p = Paths.get(targetPath);
        Path pwd = Paths.get(".");
        if (p.isAbsolute()) {
            ABSOLUTE_TARGET = p.toAbsolutePath().normalize();
            RELATIVE_TARGET = pwd.toAbsolutePath().relativize(ABSOLUTE_TARGET).normalize();
        } else {
            ABSOLUTE_TARGET = pwd.resolve(p).toAbsolutePath().normalize();
            RELATIVE_TARGET = p.normalize();
        }
    }

    private static void injectPathSentinel(ConcolicArrayObject concolic) {
        if (!concolic.isSymbolic()) {
            return;
        }
        if (!IS_SET_UP) {
            String customTarget = System.getProperty(FILE_PATH_TARGET_KEY);
            if (customTarget != null && !customTarget.isEmpty()) {
                setTargets(customTarget);
            } else {
                Path cwd = Paths.get(".").toAbsolutePath();
                if (cwd.getParent() == null) {
                    if (Logger.compileLog) {
                        Logger.DEBUG("[SENTINEL] cwd is root directory");
                    }
                    IS_DISABLED = true;
                }
                setTargets(DEFAULT_TARGET_STRING);
            }
            IS_SET_UP = true;
        }
        if (IS_DISABLED) {
            if (Logger.compileLog) {
                Logger.DEBUG("[SENTINEL] PathTraversal is disabled");
            }
            return;
        }
        // try {
        //     Object res = interop.invokeMember(pathObj.getConcreteObject(), "toString");
        // } catch (Exception e) {
        //     Logger.WARNING("Failed to invoke toString: " + e);
        //     return;
        // }
        String name = "PT";
        injectSentinel(concolic, ABSOLUTE_TARGET.toString(), name);
        injectSentinel(concolic, RELATIVE_TARGET.toString(), name);
    }

    public static void wrapFilePathTraversal(String className, String methodName, Object[] args, String signature) {
        if (Logger.compileLog) {
            Logger.DEBUG("[SENTINEL] " + className + "." + methodName + signature);
        }
        if (signature.startsWith("(Ljava/io/File;")) {
            ConcolicObjectImpl arg1 = (ConcolicObjectImpl) (methodName.equals("<init>") ? args[1] : args[0]);
            ConcolicObjectImpl fileStr = (ConcolicObjectImpl) arg1.getOrCreateField(0);
            injectPathSentinel((ConcolicArrayObject) fileStr.getOrCreateField(0));
        } else if (signature.startsWith("(Ljava/lang/String;")) {
            ConcolicObjectImpl fileStr = (ConcolicObjectImpl) (methodName.equals("<init>") ? args[1] : args[0]);
            injectPathSentinel((ConcolicArrayObject) fileStr.getOrCreateField(0));
        } else if (signature.startsWith("(Ljava/nio/file/Path;")) {
            ConcolicObjectImpl pathObj = (ConcolicObjectImpl) (methodName.equals("<init>") ? args[1] : args[0]);
            injectPathSentinel((ConcolicArrayObject) pathObj.getOrCreateField(1));
            if (signature.startsWith("(Ljava/nio/file/Path;Ljava/nio/file/Path;")) {
                ConcolicObjectImpl pathObj2 = (ConcolicObjectImpl) (methodName.equals("<init>") ? args[2] : args[1]);
                injectPathSentinel((ConcolicArrayObject) pathObj2.getOrCreateField(1));
            }
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SENTINEL] Not target: " + className + "." + methodName + signature);
            }
        }
    }

    public static void wrapOsCommandInjection(String className, String methodName, Object[] args, String signature) {
        if (Logger.compileLog) {
            Logger.DEBUG("[SENTINEL] wrapOsCommandInjection: " + className + "." + methodName + signature);
        }
        if (signature.startsWith("([Ljava/lang/String;")) {
            ConcolicObjectImpl arg0 = (ConcolicObjectImpl) args[0];
            if (arg0.getConcreteSize() == 0) {
                if (Logger.compileLog) {
                    Logger.DEBUG("[SENTINEL] cmd str array is empty");
                }
                return;
            }
            ConcolicObjectImpl firstCmdStr = (ConcolicObjectImpl) arg0.getOrCreateField(0);
            injectCMDI((ConcolicArrayObject) firstCmdStr.getOrCreateField(0));
        } else if (signature.equals("()Ljava/lang/Process;")) {
            try {
                ConcolicObjectImpl thisObj = (ConcolicObjectImpl) args[0];
                ConcolicObjectImpl listObj = (ConcolicObjectImpl) thisObj.getOrCreateField(0);
                if (Logger.compileLog) {
                    Logger.DEBUG("[SENTINEL] invoking to get cmd str");
                }
                StaticObject firstCmdStrSO = (StaticObject) interop.invokeMember(listObj.getConcreteObject(), "get", 0);
                ConcolicObjectImpl firstCmdStr = (ConcolicObjectImpl) ConcolicHelper.toConcolic(firstCmdStrSO);
                injectCMDI((ConcolicArrayObject) firstCmdStr.getOrCreateField(0));
            } catch (Exception e) {
                if (Logger.compileLog) {
                    synchronized (Z3Helper.getInstance()) {
                        Logger.DEBUG("[SENTINEL] failed to get cmd str: " + e);
                    }
                }
            }
        } else {
            if (Logger.compileLog) {
                Logger.DEBUG("[SENTINEL] Not target: " + className + "." + methodName + signature);
            }
        }
    }

    public static final String HONEYPOT_CLASS_NAME = "jaz.Zer";
    public static final String HONEYPOT_LIBRARY_NAME = "jazzer_honeypot";

    public static void wrapReflectiveCallToClass(String className, String methodName, Object[] args, String signature) {
        String name = "Reflection";
        switch (signature) {
            case "(Ljava/lang/String;)Ljava/lang/Class;":
            case "(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;":
            case "(Ljava/lang/String;Z)Ljava/lang/Class;": {
                ConcolicObjectImpl argStr = (ConcolicObjectImpl) (className.equals("java/lang/Class") ? args[0] : args[1]);
                if (argStr.isSymbolic()) {
                    injectSentinel((ConcolicArrayObject) argStr.getOrCreateField(0), HONEYPOT_CLASS_NAME, name);
                }
                break;
            }
            case "(Ljava/lang/Module;Ljava/lang/String;)Ljava/lang/Class;": {
                ConcolicObjectImpl argStr = (ConcolicObjectImpl) (className.equals("java/lang/Class") ? args[1] : args[2]);
                if (argStr.isSymbolic()) {
                    injectSentinel((ConcolicArrayObject) argStr.getOrCreateField(0), HONEYPOT_CLASS_NAME, name);
                }
                break;
            }
            default:
                break;
        }
    }

    public static void wrapReflectiveCallToLibrary(String className, String methodName, Object[] args, String signature) {
        if (signature.startsWith("(Ljava/lang/String;")) {
            ConcolicObjectImpl argStr = (ConcolicObjectImpl) (className.equals("java/lang/System") ? args[0] : args[1]);
            if (argStr.isSymbolic()) {
                injectSentinel((ConcolicArrayObject) argStr.getOrCreateField(0), HONEYPOT_LIBRARY_NAME, "CallToLib");
            }
        }
    }

    public static void wrapServerSideRequestForgery(String className, String methodName, Object[] args, String signature) {
        boolean isSpec = false;
        boolean isProtocol = false;
        ConcolicObjectImpl hostStr = null;
        ConcolicInt port = null;
        String classAndMethodName = className + "." + methodName;
        switch (classAndMethodName) {
            case "java/net/Socket.connect":
            case "java/net/SocketImpl.connect":
            case "java/net/SocksSocketImpl.connect":
            case "java/nio/channels/SocketChannel.connect":
            case "sun/nio/ch/SocketAdaptor.connect":
            case "jdk/internal/net/http/PlainHttpConnection.connect":
                if (signature.startsWith("(Ljava/net/SocketAddress;")) {
                    ConcolicObjectImpl arg = (ConcolicObjectImpl) args[1];                      // Ljava/net/SocketAddress;
                    ConcolicObjectImpl holder = (ConcolicObjectImpl) arg.getOrCreateField(0);   // Ljava/net/InetSocketAddress$InetSocketAddressHolder;
                    hostStr = (ConcolicObjectImpl) holder.getOrCreateField(0);                  // Ljava/lang/String;
                    port = (ConcolicInt) holder.getOrCreateField(2);
                } else if (signature.startsWith("(Ljava/net/InetAddress;I")) {
                    ConcolicObjectImpl arg = (ConcolicObjectImpl) args[1];                      // InetAddress
                    ConcolicObjectImpl holder = (ConcolicObjectImpl) arg.getOrCreateField(0);   // InetAddressHolder
                    hostStr = (ConcolicObjectImpl) holder.getOrCreateField(1);                  // Ljava/lang/String;
                    port = (ConcolicInt) args[2];
                } else if (signature.startsWith("(Ljava/lang/String;I")) {
                    hostStr = (ConcolicObjectImpl) args[1];
                    port = (ConcolicInt) args[2];
                }
                break;
            case "java/net/URL.<init>":
                if (signature.equals("(Ljava/net/URL;Ljava/lang/String;Ljava/net/URLStreamHandler;)V")) {
                    ConcolicObjectImpl specStr = (ConcolicObjectImpl) args[2];
                    hostStr = specStr;
                    isSpec = true;
                } else if (signature.equals("(Ljava/lang/String;Ljava/lang/String;ILjava/lang/String;Ljava/net/URLStreamHandler;)V")) {
                    ConcolicObjectImpl protocolStr = (ConcolicObjectImpl) args[1];
                    hostStr = protocolStr;
                    isProtocol = true;
                }
                break;
        }
        if ((hostStr == null || !hostStr.isSymbolic()) && (port == null || !port.isSymbolic())) {
            if (Logger.compileLog) {
                Logger.DEBUG("[SENTINEL] No target or symbolic: " + className + "." + methodName + signature);
            }
            return;
        }

        String name = "SSRF";
        if (hostStr != null && hostStr.isSymbolic()) {
            ConcolicArrayObject ba = (ConcolicArrayObject) hostStr.getOrCreateField(0);
            if (isSpec) {
                injectSentinel(ba, "http://", name);
                injectSentinel(ba, "https://", name);
                injectSentinel(ba, "gopher://", name);
                injectSentinel(ba, "ftp://", name);
                injectSentinel(ba, "file:", name);
                injectSentinel(ba, "jar:", name);
                injectSentinel(ba, "jdbc:", name);
                injectSentinel(ba, "ldap:", name);
                injectSentinel(ba, "ldaps:", name);
                injectSentinel(ba, "rmi:", name);
            } else if (isProtocol) {
                injectSentinel(ba, "http", name);
                injectSentinel(ba, "https", name);
                injectSentinel(ba, "gopher", name);
                injectSentinel(ba, "ftp", name);
                injectSentinel(ba, "file", name);
                injectSentinel(ba, "jar", name);
                injectSentinel(ba, "jdbc", name);
                injectSentinel(ba, "ldap", name);
                injectSentinel(ba, "ldaps", name);
                injectSentinel(ba, "rmi", name);
            } else {
                injectSentinel(ba, "j.c/", name);
                injectSentinel(ba, "j.co/", name);
                injectSentinel(ba, "j.com/", name);
            }
        }
        if (port != null && port.isSymbolic()) {
            int portVal = port.getConcreteValue();
            if (portVal < 0 || portVal > 65535) {
                List<BoolExpr> portConds = new ArrayList<>();
                portConds.add(Z3Helper.mkBVSGE(port.getExpr(), Z3Helper.getInstance().zeroExpr));
                portConds.add(Z3Helper.mkBVSLT(port.getExpr(), Z3Helper.mkBV(65535, 32)));
                injectSentinelCond(portConds, name);
            }
        }
    }

    public static void wrapXPathInjection(String className, String methodName, Object[] args, String signature) {
        if (!signature.equals("(Ljava/lang/String;)Ljavax/xml/xpath/XPathExpression;")) {
            if (Logger.compileLog) {
                Logger.WARNING("[SENTINEL] Need impl: " + signature);
            }
            return;
        }
        ConcolicObjectImpl arg = (ConcolicObjectImpl) args[1];
        ConcolicArrayObject argStr = (ConcolicArrayObject) arg.getOrCreateField(0);
        if (!argStr.isSymbolic()) {
            if (Logger.compileLog) {
                Logger.DEBUG("[SENTINEL] It's not symbolic: " + className + "." + methodName + signature);
            }
            return;
        }

        Logger.SOLVER("[SENTINEL] " + className + "." + methodName + signature);
        char[] sentinels = {'"', '\'', '\\'};
        for (int i = 0; i < argStr.getConcreteSize(); i++) {
            ConcolicByte concolic = (ConcolicByte) argStr.getOrCreateField(i);
            if (!concolic.isSymbolic()) {
                continue;
            }
            for (char sentinel : sentinels) {
                List<BoolExpr> conds = new ArrayList<BoolExpr>();
                conds.add(Z3Helper.mkEq(Z3Helper.convertBitVecWidth((BitVecExpr) concolic.getExprWithInit(), 8), Z3Helper.mkBV(sentinel, 8)));
                String identifier = "Sentinel-" + ConcolicVariableInfo.sentinelExprLists.size() + "-" + "XPATH";
                ConcolicVariableInfo.sentinelExprLists.add(conds);
                ConcolicVariableInfo.sentinelIdentifierList.add(identifier);
                Logger.SOLVER("[SENTINEL] Added XPath sentinel");
            }
        }
    }
}
