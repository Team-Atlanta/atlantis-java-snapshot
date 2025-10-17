package com.oracle.truffle.api.concolic;

import com.oracle.truffle.api.frame.VirtualFrame;
import com.microsoft.z3.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.*;

public class ConcolicVariableInfo {
    public static Map<String, ConcolicVariableInfo> constVariableMap;
    public static List<List<BoolExpr>> sentinelExprLists;
    public static List<String> sentinelIdentifierList;
    public static SortedMap<BitVecExpr, String> oomExprMap;

    static {
        constVariableMap = new ConcurrentHashMap<String, ConcolicVariableInfo>();
        sentinelExprLists = Collections.synchronizedList(new ArrayList<List<BoolExpr>>());
        sentinelIdentifierList = Collections.synchronizedList(new ArrayList<String>());
        oomExprMap = Collections.synchronizedSortedMap(new TreeMap<BitVecExpr, String>());
    }

    public static void reset() {
        constVariableMap = new ConcurrentHashMap<String, ConcolicVariableInfo>();
        sentinelExprLists = Collections.synchronizedList(new ArrayList<List<BoolExpr>>());
        sentinelIdentifierList = Collections.synchronizedList(new ArrayList<String>());
        oomExprMap = Collections.synchronizedSortedMap(new TreeMap<BitVecExpr, String>());
    }

    public static ConcolicVariableInfo getVariableInfo(String variableName) {
        return constVariableMap.get(variableName);
    }

    public static void setVariableInfo(String variableName, ConcolicVariableInfo info) {
        constVariableMap.put(variableName, info);
    }

    public String name;
    public String delimiter;
    public String delimiterInHex;
    public int blobStartIndex;   // inclusive
    public int blobEndIndex;     // exclusive
    public int length;           // current concrete length
    public int maxLength;        // if variable

    public ConcolicVariableInfo() {
        this.name = null;
        delimiter = null;
        delimiterInHex = null;
        blobStartIndex = blobEndIndex = length = maxLength = -1;
    }
    public ConcolicVariableInfo(String name) {
        this();
        this.name = name;
    }

    public ConcolicVariableInfo(String name, int blobStartIndex, int blobEndIndex) {
        this(name);
        this.blobStartIndex = blobStartIndex;
        this.blobEndIndex = blobEndIndex;
        this.length = blobEndIndex - blobStartIndex;
    }

    public boolean isVariableLength() {
        return (this.maxLength != -1);
    }

    public boolean isWithDelimiter() {
        return (this.delimiter != null);
    }

    public String getName() {
        return this.name;
    }

    public void setName(String n) {
        this.name = n;
    }

    public String getDelimiter() {
        return this.delimiter;
    }

    public void setDelimiter(String delim) {
        this.delimiter = delim;
    }

    public String getDelimiterInHex() {
        return this.delimiterInHex;
    }

    public void setDelimiterInHex(String hex) {
        this.delimiterInHex = hex;
    }

    public int getBlobStartIndex() {
        return this.blobStartIndex;
    }

    public void setBlobStartIndex(int startIndex) {
        this.blobStartIndex = startIndex;
    }

    public int getBlobEndIndex() {
        return this.blobEndIndex;
    }

    public void setBlobEndIndex(int endIndex) {
        this.blobEndIndex = endIndex;
    }

    public int getLength() {
        return this.length;
    }

    public void setLength(int len) {
        this.length = len;
    }

    public int getMaxLength() {
        return this.maxLength;
    }

    public void setMaxLength(int len) {
        this.maxLength = len;
    }

}
