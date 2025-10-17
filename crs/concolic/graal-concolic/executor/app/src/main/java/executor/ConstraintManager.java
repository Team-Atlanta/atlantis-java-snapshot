package executor;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.io.IOException;

import com.oracle.truffle.api.concolic.*;
import org.graalvm.polyglot.Context;

import java.util.*;
import java.util.stream.Collectors;

import com.microsoft.z3.*;

class VariableNameComparator implements Comparator<String> {
    public int compare(String x, String y) {
        int x_idx = Integer.valueOf(x.split("_")[1]);
        int y_idx = Integer.valueOf(y.split("_")[1]);
        return x_idx - y_idx;
    }
}

// Store the branch and associated variables
class BranchConstraintInfo {
    public ConcolicBranch branch;
    // stores variables. if multiExpr, stores all variables
    public HashSet<String> variables;
    // stores variables of each expr of multiExpr
    public ArrayList<HashSet<String>> multiVariables;
    public boolean is_multiExpr;
    public int multiExprSize;

    public BranchConstraintInfo(ConcolicBranch branch) {
        this.branch = branch;
        if (this.branch.isMultiExpr()) {
            this.is_multiExpr = true;
            this.multiExprSize = this.branch.getExprArrayLength();
            this.variables = new HashSet<String>();
            this.multiVariables = new ArrayList<HashSet<String>>();

            // collect variables per each expr
            for (int i=0; i<this.multiExprSize; ++i) {
                HashSet<String> variables = new HashSet<String>();
                collectVariables(this.branch.getExpr(i), variables);
                this.multiVariables.add(variables);
            }
            // collect variables in all and expr.
            collectVariables(this.branch.getAllAndExpr(), this.variables);
        } else {
            this.variables = new HashSet<String>();
            this.multiVariables = null;
            collectVariables(branch.getExpr(), this.variables);
        }
    }

    public boolean isMultiExpr() {
        return this.is_multiExpr;
    }

    public ConcolicBranch getBranch() {
        return this.branch;
    }

    public int getMultiExprSize() {
        return this.multiExprSize;
    }

    public static void collectVariables(Expr<?> expr, Set<String> variables) {
        if (expr == null) {
            return;
        }
        Set<Expr<?>> visited = new HashSet<>();
        Deque<Expr<?>> stack = new ArrayDeque<>();
        stack.push(expr);
        while (!stack.isEmpty()) {
            Expr<?> cur = stack.pop();
            if (cur == null || visited.contains(cur)) {
                continue;
            }
            visited.add(cur);
            if (cur.isConst()
                    && cur.getNumArgs() == 0
                    && !cur.isNumeral()
                    && !cur.isTrue()
                    && !cur.isFalse()) {
                variables.add(cur.toString().strip());
            } else {
                for (Expr<?> child : cur.getArgs()) {
                    if (child != null && !visited.contains(child)) {
                        stack.push(child);
                    }
                }
            }
        }
    }
}

public class ConstraintManager {
    private static byte[] originalBlob;
    private static List<byte[]> blobs;
    private static List<String> branchIdentifiers;

    private static boolean removeDuplicatedBranches = true;

    public  static boolean isTargetSet;
    private static String targetClassName;
    private static String targetMethodName;
    private static int targetBytecodeOffset;

    public static String outDir;
    public static int rid = 0;
    public static int cnt = 0;
    public static int pid = 0;
    public static final HashSet<String> whiteList;
    public static final HashMap<String, String> blacklistedPackages;
    public static ArrayList<String> containsClassBlacklist;
    public static ArrayList<String> containsMethodBlacklist;
    static {
        whiteList = new HashSet<String>();
        // whiteList.add("java/lang/Integer.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Long.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Short.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Byte.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Boolean.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Character.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Float.equals(Ljava/lang/Object;)Z");
        // whiteList.add("java/lang/Double.equals(Ljava/lang/Object;)Z");

        blacklistedPackages = new HashMap<String, String>();
        blacklistedPackages.put("java/nio/Buffer", "");
        blacklistedPackages.put("java/lang/StringCoding", "");
        blacklistedPackages.put("java/lang/String", "");
        blacklistedPackages.put("java/lang/StringLatin1", "");
        blacklistedPackages.put("java/lang/StringUTF16", "");
        blacklistedPackages.put("java/util/Arrays", "");
        blacklistedPackages.put("java/util/TreeMap", "");
        blacklistedPackages.put("java/lang/CharacterDataLatin1", "");
        blacklistedPackages.put("jdk/internal/util/ArraysSupport", "");

        blacklistedPackages.put("java/util/concurrent/ConcurrentHashMap", "");
        blacklistedPackages.put("java/util/LinkedHashMap", "");
        blacklistedPackages.put("java/util/HashMap", "");
        blacklistedPackages.put("java/util/WeakHashMap", "");
        blacklistedPackages.put("java/util/IdentityHashMap", "");
        blacklistedPackages.put("com/oracle/svm/core/WeakIdentityHashMap", "");

        blacklistedPackages.put("java/io/SequenceInputStream", "");
        blacklistedPackages.put("java/io/BufferedInputStream", "");
        blacklistedPackages.put("java/io/InputStream", "");
        blacklistedPackages.put("java/io/PushbackInputStream", "");
        blacklistedPackages.put("java/io/FilterInputStream", "");
        blacklistedPackages.put("java/io/ObjectInputStream", "");
        blacklistedPackages.put("java/io/ByteArrayInputStream", "");
        blacklistedPackages.put("java/io/FileInputStream", "");
        blacklistedPackages.put("java/io/DataInputStream", "");
        blacklistedPackages.put("java/util/zip/InflaterInputStream", "");
        blacklistedPackages.put("java/util/zip/CheckedInputStream", "");
        // blacklistedPackages.put("java/util/zip/GZIPInputStream", "");
        blacklistedPackages.put("sun/security/util/DerInputStream", "");
        blacklistedPackages.put("sun/nio/ch/SocketInputStream", "");
        blacklistedPackages.put("sun/nio/ch/ChannelInputStream", "");

        // Number-related classes
        blacklistedPackages.put("java/lang/Integer", "");
        blacklistedPackages.put("java/lang/Long", "");
        blacklistedPackages.put("java/lang/Short", "");
        blacklistedPackages.put("java/lang/Byte", "");
        blacklistedPackages.put("java/lang/Boolean", "");
        blacklistedPackages.put("java/lang/Character", "");
        blacklistedPackages.put("java/lang/Float", "");
        blacklistedPackages.put("java/lang/Double", "");
        blacklistedPackages.put("java/io/DataInputStream", "");

        // tokenize
        blacklistedPackages.put("com/sun/org/apache/xpath/internal/compiler/Lexer", "");

        containsClassBlacklist = new ArrayList<String>();
        // containsClassBlacklist.add("InputStream".toLowerCase());
        containsClassBlacklist.add("UTF_8$Decoder".toLowerCase());
        containsClassBlacklist.add("MessageDigest".toLowerCase());
        containsClassBlacklist.add("Hashing".toLowerCase());
        containsClassBlacklist.add("SHA256".toLowerCase());
        containsClassBlacklist.add("SHA1".toLowerCase());
        containsClassBlacklist.add("SHA3".toLowerCase());
        containsClassBlacklist.add("MD5".toLowerCase());
        containsClassBlacklist.add("Digest".toLowerCase());
        containsClassBlacklist.add("regex".toLowerCase());

        containsMethodBlacklist = new ArrayList<String>();
        containsMethodBlacklist.add("compress".toLowerCase());

    }

    private static CoverageManager coverageManager = null;

    public static class BranchCase {
        public String branchIdentifier;
        public Integer branchValue;

        public BranchCase(String branchIdentifier, Integer branchValue) {
            this.branchIdentifier = branchIdentifier;
            this.branchValue = branchValue;
        }

        public String toString() {
            return this.branchIdentifier + " " + this.branchValue;
        }

        public boolean equals(Object obj) {
            if (obj == this) {
                return true;
            }
            if (!(obj instanceof BranchCase)) {
                return false;
            }
            BranchCase other = (BranchCase) obj;
            return this.branchIdentifier.equals(other.branchIdentifier) && this.branchValue.equals(other.branchValue);
        }

        public int hashCode() {
            return this.branchIdentifier.hashCode() + this.branchValue.hashCode();
        }
    }

    static {
        blobs = new ArrayList<>();
        branchIdentifiers = new ArrayList<String>();

        targetClassName = "";
        targetMethodName = "";
        targetBytecodeOffset = -1;
        isTargetSet = false;
    }

    private static ArrayList<BoolExpr> inputConstraints = new ArrayList<BoolExpr>(8192);

    public static void setCoverageManager(CoverageManager coverageManager) {
        ConstraintManager.coverageManager = coverageManager;
    }

    public static CoverageManager getCoverageManager() {
        if (coverageManager == null) {
            return null;
        }
        if (!coverageManager.isEnabled()) {
            return null;
        }
        return coverageManager;
    }

    public static void setTarget(String className, String methodName, int bytecodeOffset) {
        targetClassName = className;
        targetMethodName = methodName;
        targetBytecodeOffset = bytecodeOffset;
        isTargetSet = true;
    }

    public static void unsetTarget() {
        targetClassName = "";
        targetMethodName = "";
        targetBytecodeOffset = -1;
        isTargetSet = false;
    }

    public static void addInputConstraint(BoolExpr inputConstraint) {
        inputConstraints.add(inputConstraint);
    }

    public static void getResults(Model m, String branchIdentifier) throws IOException {
        // get sorted variable names / expr map
        FuncDecl<?>[] constDecls = m.getConstDecls();
        String[] variableNames = new String[constDecls.length];
        HashMap<String, Expr<?>> variableMap = new HashMap<String, Expr<?>>();
        for (int i=0; i<constDecls.length; ++i) {
            variableNames[i] = constDecls[i].getName().toString();
            Expr<?> expr = m.getConstInterp(constDecls[i]);
            variableMap.put(variableNames[i], expr);
        }
        Arrays.sort(variableNames, new VariableNameComparator());

        // build blob
        ArrayList<Byte> blobList = new ArrayList<Byte>();
        for (String variableName: variableNames) {
            Expr<?> expr = variableMap.get(variableName);
            String value = getConvertedValue(variableName, expr);
            Logger.SOLVER(String.format("Solved variable %s : %s", variableName, value));
            if (originalBlob != null) {
                putVariableOnBlob(variableName, expr, blobList);
            }
        }
        if (originalBlob != null) {
            fillBlobWithOriginalsUntilSize(originalBlob.length, blobList);
            byte[] blob = new byte[blobList.size()];
            for (int i=0; i<blobList.size(); ++i) {
                Byte b = blobList.get(i);
                blob[i] = b.byteValue();
            }
            // write blob at here

            blobs.add(blob);
            branchIdentifier = branchIdentifier.replace("/", ".");
            branchIdentifiers.add(branchIdentifier);
            if (outDir != null && !outDir.isEmpty()) {
                saveBlobToDir(blob, branchIdentifier);
            }
            Logger.SOLVER("Adding as blob filename index: " + blobs.size());
        }
    }

    public static void saveBlobToDir(byte[] blob, String branchIdentifier) throws IOException {
        Path dirPath = Paths.get(outDir);
        if (!Files.exists(dirPath)) {
            Files.createDirectories(dirPath);
        }
        long time = System.currentTimeMillis();
        if (branchIdentifier.length() > 100) {
            branchIdentifier = branchIdentifier.substring(0, 100);
        }

        String fileName = "blob-" + time + branchIdentifier + "-cnt-" + cnt + "-pid-" + pid + "-rid-" + rid + ".bin";
        cnt += 1;
        Path outputPath = dirPath.resolve(fileName);
        Files.write(outputPath, blob);
        System.out.println("[Executor] Saved blob to: " + outputPath.toAbsolutePath());
    }

    public static void solveBranches(List<BoolExpr> pathConstraintsList, String dotIdentifier, int branchIdx) {
        try {
            if (branchIdx != -1) {
                solveBranches(pathConstraintsList, dotIdentifier);
            } else {
                solveBranches(pathConstraintsList, "Non-negated.Constraints");
            }
        } catch (Exception e) {
            Logger.SOLVER(e.getMessage());
            e.printStackTrace();
        }
    }

    public static void solveBranches(List<BoolExpr> pathConstraintsList, String dotIdentifier) throws IOException {
        Solver solver = Z3Helper.mkSolver();
        Params p = Z3Helper.mkParams();
        // solver timeout
        p.add("timeout", 60 * 1000);  // Timeout in milliseconds, 60 seconds
        solver.setParameters(p);
        for (BoolExpr pathConstraint : pathConstraintsList) {
            solver.add(pathConstraint);
            Logger.SOLVER_VERBOSE("" + pathConstraint);
        }
        for (BoolExpr inputConstraint : inputConstraints) {
            solver.add(inputConstraint);
            Logger.SOLVER_VERBOSE(inputConstraint.toString());
        }


        Status s = solver.check();
        if (s == Status.SATISFIABLE) {
            Logger.SOLVER("Solver result: SAT");
            getResults(solver.getModel(), dotIdentifier);
        } else if (s == Status.UNSATISFIABLE) {
            Logger.SOLVER("Solver result: UNSAT");
        } else {
            Logger.SOLVER("Solver result: UNKNOWN -- timeout");
        }
    }

    public static boolean addRelatedVariables(HashSet<String> variables, HashSet<String> involvedVariables) {
        boolean matchingVariableFound = false;
        String s = "";
        for (String variable : variables) {
            s += variable + " ";
        }
        Logger.DEBUG("Branch variables: " + s);
        for (String variable : variables) {
            if (involvedVariables.contains(variable)) {
                // if found, break.
                matchingVariableFound = true;
                Logger.DEBUG("Found matching variable: " + variable);
                break;
            }
        }
        // if found, add them all!
        if (matchingVariableFound) {
            s = "";
            for (String variable : variables) {
                s += variable + " ";
                involvedVariables.add(variable);
            }
            Logger.DEBUG("Added variables: " + s);
        }
        return matchingVariableFound;
    }

    public static void _solveNegatedBranch(int idx,
                    ArrayList<BranchConstraintInfo> branchConstraintInfos,
                    BoolExpr negatedTargetExpr,
                    BranchConstraintInfo targetInfo,
                    int multiExprIdx) {

        ArrayList<BoolExpr> pathConstraintsList = new ArrayList<BoolExpr>();
        HashSet<Integer> branchIndexToAdd = new HashSet<Integer>();
        HashSet<String> involvedVariables = new HashSet<String>(targetInfo.variables);

        String s = "";
        for (String variable : involvedVariables) {
            s += variable + " ";
        }
        Logger.SOLVER_VERBOSE("Initial variables: " + s);
        // get branch idx list to add
        while (true) {
            int variableSize = involvedVariables.size();

            for (int i=idx-1; i>=0; --i) {
                Integer I = Integer.valueOf(i);
                // ignore already added branch
                if (branchIndexToAdd.contains(I)) {
                    continue;
                }
                BranchConstraintInfo info = branchConstraintInfos.get(i);
                /*
                 * YJ: multiExpr is handled by iterating all varaibles in
                 *     info.variables, coming from branch.getAllAndExpr()
                 */
                boolean matchFound = addRelatedVariables(info.variables, involvedVariables);
                if (matchFound) {
                    branchIndexToAdd.add(I);
                }
            }

            // if nothing added, break!
            if (involvedVariables.size() == variableSize) {
                Logger.DEBUG("No more variables to add for idx: " + idx);
                break;
            }
            s = "";
            for (String variable : involvedVariables) {
                s += variable.toString() + " ";
            }
            Logger.SOLVER_VERBOSE("Total variables: " + s);
        }
        ArrayList<Integer> branchIndexToAddList = new ArrayList<Integer>(branchIndexToAdd);
        Collections.sort(branchIndexToAddList, Collections.reverseOrder());
        pathConstraintsList.add(negatedTargetExpr);
        for (Integer i : branchIndexToAddList) {
            BranchConstraintInfo info = branchConstraintInfos.get(i);
            // XXX: handle Multi Expr
            pathConstraintsList.add(info.branch.getExpr());
        }
        String branchIdentifier = "" + multiExprIdx + "." + targetInfo.branch.getDotIdentifier();
        solveBranches(pathConstraintsList, branchIdentifier, idx);
    }

    public static void solveByNegatingMultiExpr(int idx, ArrayList<BranchConstraintInfo> branchConstraintInfos) {
        // ignore debug case for now
        if (idx == -1) {
            return;
        }
        BranchConstraintInfo targetInfo = branchConstraintInfos.get(idx);
        ConcolicBranch targetBranch = targetInfo.getBranch();
        if (!targetBranch.isMultiExpr()) {
            throw new RuntimeException("[ConstraintManager] Branch must be Multi Expr: " + targetBranch.getExpr());
        }
        for (int i=0; i<targetInfo.getMultiExprSize(); ++i) {
            BoolExpr negatedTargetExpr = targetInfo.branch.getFlippedExpr(i);
            _solveNegatedBranch(idx, branchConstraintInfos, negatedTargetExpr, targetInfo, i);
        }
    }

    public static void solveByNegatingBranch(int idx, ArrayList<BranchConstraintInfo> branchConstraintInfos) {
        // ignore debug case for now
        if (idx == -1) {
            return;
        }
        BranchConstraintInfo targetInfo = branchConstraintInfos.get(idx);
        ConcolicBranch targetBranch = targetInfo.getBranch();

        if (targetBranch.isMultiExpr()) {
            throw new RuntimeException("[ConstraintManager] Multi Expr must not reach here: " + targetBranch.getAllAndExpr());
        }

        BoolExpr negatedTargetExpr = targetInfo.branch.getFlippedExpr();
        _solveNegatedBranch(idx, branchConstraintInfos, negatedTargetExpr, targetInfo, 0);
    }

    public static String getConvertedValue(String variableName, Expr<?> expr) {
        String[] nameArray = variableName.split("_");
        switch (nameArray[0]) {
            case "I":
                return String.format("0x%08x", Long.valueOf(expr.toString()));
            case "B":
                return String.format("0x%02x", Long.valueOf(expr.toString()));
            case "S":
                return String.format("0x%04x", Long.valueOf(expr.toString()));
            default:
                return expr.toString();
        }
    }

    public static void fillBlobWithOriginalsUntilSize(int n, ArrayList<Byte> blobList) {
        int currentLength = blobList.size();
        if (n == currentLength) {
            return;
        }

        if (n < currentLength) {
            return;
            /*
            throw new RuntimeException(String.format("Blob gen failed: N %d for length %d",
                        n, currentLength));
            */
        }

        for (int i=currentLength; i < n; ++i) {
            blobList.add(Byte.valueOf(originalBlob[i]));
        }
    }

    public static void putVariableOnBlob(String variableName, Expr<?> expr, ArrayList<Byte> blobList) {
        String[] nameArray = variableName.split("_");
        ConcolicVariableInfo variableInfo = ConcolicVariableInfo.getVariableInfo(variableName);
        if (variableInfo == null) {
            // Here, we do not check Logger.compileLog
            Logger.DEBUG("[putVariableOnBlob]: skipping " + variableName);
            return;
        }

        if (variableInfo.blobStartIndex == -1 || variableInfo.blobEndIndex == -1) {
            // Here, we do not check Logger.compileLog
            Logger.DEBUG(String.format("[putVariableOnBlob] range (%d, %d) for variable %s",
                        variableInfo.blobStartIndex,
                        variableInfo.blobEndIndex,
                        variableName));
            return;
        }
        int currentLength = blobList.size();
        // Here, we do not check Logger.compileLog
        Logger.DEBUG(String.format("[putVariableOnBlob]: %s (%d, %d), length %d class %s",
                                    variableName,
                                    variableInfo.blobStartIndex,
                                    variableInfo.blobEndIndex,
                                    currentLength,
                                    expr.getClass().getName().toString()));

        fillBlobWithOriginalsUntilSize(variableInfo.blobStartIndex, blobList);

        switch (nameArray[0]) {
            case "B": {
                BitVecNum numExpr = (BitVecNum) expr;
                int intValue = numExpr.getInt();
                blobList.add(Byte.valueOf(Integer.valueOf(intValue).byteValue()));
            }
            default:
                break;
        }
    }

    public static ArrayList<ConcolicBranch> filterBranches(ArrayList<ConcolicBranch> branchList) {
        ArrayList<ConcolicBranch> candidateBranches = new ArrayList<ConcolicBranch>();
        HashSet<Integer> visitedBranches = new HashSet<Integer>();
        for (ConcolicBranch b : branchList) {
            boolean isBlacklisted = false;
            if (blacklistedPackages.containsKey(b.getClassName())) {
                isBlacklisted = true;
            } else {
                String className = b.getClassName().toLowerCase();
                for (String blacklistedClassName : containsClassBlacklist) {
                    if (className.contains(blacklistedClassName)) {
                        isBlacklisted = true;
                        break;
                    }
                }
                if (!isBlacklisted) {
                    String methodName = b.getMethodName().toLowerCase();
                    for (String blacklistdMethodName : containsMethodBlacklist) {
                        if (methodName.contains(blacklistdMethodName)) {
                            isBlacklisted = true;
                            break;
                        }
                    }
                }
            }
            if (isBlacklisted) {
                if (whiteList.contains(b.getClassName() + "." + b.getMethodName())) {
                    isBlacklisted = false;
                }
            }

            // TODO: Temporarily patch: filter duplicated branches for testing
            //                  Should be disabled for the final version
            // else if (removeDuplicatedBranches && visitedBranches.contains(b.backtraceHash())) {
            //     String suffix = b.isMultiExpr() ? " (multi)" : b.getExpr().toString();
            //     Logger.SOLVER("Branch filtered (duplicated): [BRANCH " + b.getIdentifier() + ", " + b.isTaken() + "] : " + suffix);
            // }
            if (isBlacklisted) {
                Logger.SOLVER_VERBOSE("Branch filtered (blacklisted package): [BRANCH " + b.getIdentifier() + ", " + b.isTaken() + "]");
            }
            else {
                candidateBranches.add(b);
                visitedBranches.add(b.backtraceHash());
            }
        }
        return candidateBranches;
    }

    private static boolean isUrgentBranch(String branch_str, List<String> partly_visited_branches) {
        if (partly_visited_branches != null) {
            for (String partly_visited_branch : partly_visited_branches) {
                if (partly_visited_branch.endsWith(branch_str)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static ArrayList<Integer> reorderUrgentBranches(
            List<BranchConstraintInfo> branchConstraintInfos,
            List<Integer> constraint_indexes,
            List<String> partly_visited_branches
        ) {
        List<Integer> urgentBranchIndexes = new ArrayList<>();
        List<Integer> nonUrgentBranchIndexes = new ArrayList<>();
        ArrayList<Integer> result = new ArrayList<>();
        for (int i : constraint_indexes) {
            BranchConstraintInfo info = branchConstraintInfos.get(i);
            String branch_str = info.getBranch().getClassName() + "." + info.getBranch().getMethodName() + ":" + info.getBranch().getBytecodeOffset();
            if (isUrgentBranch(branch_str, partly_visited_branches)) {
                Logger.SOLVER("[+] Urgent branch: " + branch_str);
                urgentBranchIndexes.add(i);
            }
            else {
                nonUrgentBranchIndexes.add(i);
            }
        }
        result.addAll(urgentBranchIndexes);
        result.addAll(nonUrgentBranchIndexes);
        return result;
    }

    public static void processConstraints() {
        // all collected branches
        ArrayList<ConcolicBranch> branchList = ConcolicBranch.getBranchList();
        // removed blacklisted branches
        ArrayList<ConcolicBranch> candidateBranches = filterBranches(branchList);
        List<String> partly_visited_branches = new ArrayList<>();
        if (getCoverageManager() != null) {
            partly_visited_branches = getCoverageManager().getPartlyVisitedBranches();
        }

        // create info to link branch <-> associated variables
        ArrayList<BranchConstraintInfo> branchConstraintInfos = new ArrayList<BranchConstraintInfo>(candidateBranches.size());

        // create info
        for (ConcolicBranch branch : candidateBranches) {
            // include MultiExpr (lookup/table switch)
            /*
            if (branch.isMultiExpr()) {
                continue;
            }
            */
            // internally collects variables
            BranchConstraintInfo info = new BranchConstraintInfo(branch);
            branchConstraintInfos.add(info);
        }

        ArrayList<Integer> constraint_indexes = new ArrayList<>();
        for (int i=branchConstraintInfos.size()-1; i >= 0; --i) {
            constraint_indexes.add(i);
        }
        if (getCoverageManager() != null) {
            // Postpone non-urgent branches
            constraint_indexes = reorderUrgentBranches(branchConstraintInfos, constraint_indexes, partly_visited_branches);
            Logger.SOLVER("Coverage manager is enabled, Reordered branches");
        }
        else {
            Logger.SOLVER("Coverage manager is not enabled, Do not reorder branches, use original order");
        }

        Logger.SOLVER("Starting to negate branches");

        long solving_start_time = System.currentTimeMillis();

        if (isTargetSet) {
            targetClassName = targetClassName.replace(".", "/");
        }

        for (int i : constraint_indexes) {
            try {
                BranchConstraintInfo info = branchConstraintInfos.get(i);
                if (isTargetSet) {
                    if (!targetClassName.equals(info.getBranch().getClassName())) {
                        Logger.SOLVER("Skipping branch class: " + targetClassName + " vs " + info.getBranch().getClassName());
                        continue;
                    }
                    if (!targetMethodName.equals(info.getBranch().getMethodName())) {
                        Logger.SOLVER("Skipping branch method: " + targetMethodName + " vs " + info.getBranch().getMethodName());
                        continue;
                    }
                }

                long current_time = System.currentTimeMillis();
                long elapsed_time = current_time - solving_start_time;
                // constraint solving total timeout
                if (elapsed_time > 180 * 1000) {
                    Logger.SOLVER("Timeout in solving branchlist, stoppping, total time: " + elapsed_time + "ms");
                    break;
                }
                Logger.SOLVER("Negating branch " + i);
                String branch_str = info.getBranch().getClassName() + "." + info.getBranch().getMethodName() + ":" + info.getBranch().getBytecodeOffset();
                Logger.SOLVER("[+] Negating branch " + i + " - " + branch_str);

                if (getCoverageManager() != null) {
                    getCoverageManager().addTriedBranches(Arrays.asList(branch_str));
                }

                if (info.getBranch().isMultiExpr()) {
                    solveByNegatingMultiExpr(i, branchConstraintInfos);
                } else {
                    solveByNegatingBranch(i, branchConstraintInfos);
                }
            } catch (Exception e) {
                Logger.SOLVER("Failed to generate negating blob: " + i);
            }
        }
        if (isTargetSet) {
            return;
        }
        Map<ConcolicBranch, HashSet<String>> branchVarMap = new HashMap<>();
        for (ConcolicBranch b : candidateBranches) {
            HashSet<String> branchVars = new HashSet<String>();
            if (b.isMultiExpr()) {
                for (int i = 0; i < b.getExprArrayLength(); i++) {
                    BranchConstraintInfo.collectVariables(b.getExpr(i), branchVars);
                }
            } else {
                BranchConstraintInfo.collectVariables(b.getExpr(), branchVars);
            }
            branchVarMap.put(b, branchVars);
        }
        solveSentinel(candidateBranches, branchVarMap);
        solveOOM(candidateBranches, branchVarMap);
    }

    public static void solveSentinel(List<ConcolicBranch> candidateBranches, Map<ConcolicBranch, HashSet<String>> branchVarMap) {
        for (int i = ConcolicVariableInfo.sentinelExprLists.size() - 1; i >= 0; i--) {
            List<BoolExpr> exprs = ConcolicVariableInfo.sentinelExprLists.get(i);
            String identifier = ConcolicVariableInfo.sentinelIdentifierList.get(i);
            try {
                Logger.SOLVER("Solving " + identifier);

                Set<BoolExpr> conds = new HashSet<>();
                Set<String> vars = new HashSet<>();
                for (BoolExpr expr : exprs) {
                    conds.add(expr);
                    BranchConstraintInfo.collectVariables(expr, vars);
                }
                for (ConcolicBranch b : candidateBranches) {
                    HashSet<String> branchVars = branchVarMap.get(b);
                    if (!vars.stream().filter(branchVars::contains).collect(Collectors.toSet()).isEmpty()) {
                        if (b.isMultiExpr()) {
                            for (int j = 0; j < b.getExprArrayLength(); j++) {
                                conds.add(b.getExpr(j));
                            }
                        } else {
                            conds.add(b.getExpr());
                        }
                    }
                }
                solveBranches(new ArrayList<>(conds), identifier);
            } catch (Exception e) {
                Logger.SOLVER("Failed to generate sentinel blob: " + identifier);
            }
        }
    }

    public static void solveOOM(List<ConcolicBranch> candidateBranches, Map<ConcolicBranch, HashSet<String>> branchVarMap) {
        int cnt = 0;
        Map<String, Integer> solvingCountMap = new HashMap<>();
        for (Map.Entry<BitVecExpr, String> entry : ConcolicVariableInfo.oomExprMap.reversed().entrySet()) {
            BitVecExpr expr = entry.getKey();
            String branchIdentifier = entry.getValue();
            int solvingCount = solvingCountMap.getOrDefault(branchIdentifier, 0);
            if (solvingCount < 5) {
                solvingCountMap.put(branchIdentifier, ++solvingCount);
            } else {
                Logger.SOLVER_VERBOSE("Limited " + branchIdentifier);
                continue;
            }
            String identifier = "OOM-" + (cnt++) + "-" + branchIdentifier;
            try {
                Logger.SOLVER("Solving " + identifier);

                Set<BoolExpr> conds = new HashSet<>();
                Set<String> vars = new HashSet<>();
                BranchConstraintInfo.collectVariables(expr, vars);
                while (true) {
                    int varsSize = vars.size();
                    for (ConcolicBranch b : candidateBranches) {
                        HashSet<String> branchVars = branchVarMap.get(b);
                        if (!vars.stream().filter(branchVars::contains).collect(Collectors.toSet()).isEmpty()) {
                            if (b.isMultiExpr()) {
                                for (int i = 0; i < b.getExprArrayLength(); i++) {
                                    conds.add(b.getExpr(i));
                                }
                            } else {
                                conds.add(b.getExpr());
                            }
                            vars.addAll(branchVars);
                        }
                    }
                    if (varsSize == vars.size()) {
                        break;
                    }
                }

                Optimize opt = Z3Helper.mkOptimize();
                Params p = Z3Helper.mkParams();
                p.add("timeout", 60 * 1000);  // Timeout in milliseconds, 60 seconds
                opt.setParameters(p);
                for (BoolExpr pathConstraint : conds) {
                    opt.Add(pathConstraint);
                }
                for (BoolExpr inputConstraint : inputConstraints) {
                    opt.Add(inputConstraint);
                    Logger.SOLVER_VERBOSE(inputConstraint.toString());
                }

                ArithExpr x = Z3Helper.mkBV2Int(expr, true);
                opt.MkMaximize(x);

                Status s = opt.Check();
                if (s == Status.SATISFIABLE) {
                    Logger.SOLVER("Optimize result: SAT");
                    getResults(opt.getModel(), identifier);
                } else if (s == Status.UNSATISFIABLE) {
                    Logger.SOLVER("Optimize result: UNSAT");
                } else {
                    Logger.SOLVER("Optimize result: UNKNOWN -- timeout");
                }
            } catch (Exception e) {
                Logger.SOLVER("Failed to generate OOM blob: " + identifier);
            }
        }
    }

    public static List<BranchCase> getVisitedBranchCases() {
        List<BranchCase> visitedBranchCases = new ArrayList<>();

        // all collected branches
        ArrayList<ConcolicBranch> branchList = ConcolicBranch.getBranchList();
        // removed blacklisted branches
        ArrayList<ConcolicBranch> candidateBranches = filterBranches(branchList);

        for (ConcolicBranch branch : candidateBranches) {
            visitedBranchCases.add(new BranchCase(branch.getIdentifier(), branch.isTaken() ? 1 : 0));
        }
        return visitedBranchCases;
    }

    public static List<byte[]> getGeneratedBlobs() {
        return blobs;
    }

    public static List<String> getBranchIdentifiers() {
        return branchIdentifiers;
    }

    public static void clearBlobs() {
        blobs.clear();
        branchIdentifiers.clear();
    }

    public static void setOriginalBlob(byte[] blob) {
        originalBlob = blob;
        // Here, we do not check Logger.compileLog
        Logger.DEBUG("[ConstraintManager] Original blob: " + originalBlob.toString());
    }
}
