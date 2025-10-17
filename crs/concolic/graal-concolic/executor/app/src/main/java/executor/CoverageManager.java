package executor;

import java.util.*;
import java.util.stream.Collectors;
import com.google.gson.Gson;
import java.net.Socket;
import java.io.IOException;
import java.io.OutputStream;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.io.StringWriter;
import java.io.PrintWriter;

public class CoverageManager {
    String harnessId;
    String javaHome;
    boolean isEnabled;
    int portNumber = 27664;

    private class ParentPayload {
        public String harness_id;
        public String java_home;
        public String command;
        public ParentPayload() {
            this.harness_id = harnessId;
            this.java_home = javaHome;
            this.command = null;
        }
    }

    private class UpdateSeedPayload extends ParentPayload {
        public String seed_path;
        public List<String> classes;
        public UpdateSeedPayload(String seed_path, List<String> classes) {
            super();
            this.command = "update_seed";
            this.seed_path = seed_path;
            this.classes = classes;
        }
    }

    private class AddTriedBranchesPayload extends ParentPayload {
        public List<String> tried_branches;
        public AddTriedBranchesPayload(List<String> tried_branches) {
            super();
            this.command = "add_tried_branches";
            this.tried_branches = tried_branches;
        }
    }

    private class GetPartlyVisitedBranchesPayload extends ParentPayload {
        public GetPartlyVisitedBranchesPayload() {
            super();
            this.command = "get_partly_visited_branches";
        }
    }

    public CoverageManager(String harnessId, String javaHome, int schedulerPort) {
        this.harnessId = harnessId;
        this.javaHome = javaHome;
        this.portNumber = schedulerPort;
        this.isEnabled = initEnabled();
    }

    private void TryCloseSocket(Socket socket) {
        for (int i = 0; i < 3; i++) {
            try {
                if (socket == null) {
                    return;
                }
                socket.close();
                return;
            } catch (Exception e) {
                // Ignore
            }
        }
    }

    private String sendCommand(String jsonPayload) {
        return sendCommand(jsonPayload, false);
    }

    private String sendCommand(String jsonPayload, boolean tryIfDisabled) {
        if (portNumber <= 0) {
            return null;
        }
        if (!tryIfDisabled && !isEnabled) {
            return null;
        }
        Socket socket = null;
        try {
            socket = new Socket("localhost", portNumber);

            // Set timeout to 30 seconds
            socket.setSoTimeout(30000);

            OutputStream outputStream = socket.getOutputStream();
            byte[] header = "SEEDEVAL".getBytes();
            assert header.length == 8;
            int jsonPayloadLength = jsonPayload.length();
            byte[] jsonPayloadLengthBytes = ByteBuffer.allocate(8).putLong(jsonPayloadLength).array();
            outputStream.write(header);
            outputStream.write(jsonPayloadLengthBytes);
            outputStream.write(jsonPayload.getBytes());
            outputStream.flush();

            InputStream inputStream = socket.getInputStream();
            byte[] responseHeader = new byte[8];
            inputStream.readNBytes(responseHeader, 0, 8);
            byte[] responseLengthBytes = new byte[8];
            inputStream.readNBytes(responseLengthBytes, 0, 8);
            int responseLength = (int) ByteBuffer.wrap(responseLengthBytes).getLong();
            byte[] responseBody = new byte[responseLength];

            // Until reaching responseLength, read the response
            int bytesRead = 0;
            while (bytesRead < responseLength) {
                bytesRead += inputStream.read(responseBody, bytesRead, responseLength - bytesRead);
            }
            String response = new String(responseBody);
            TryCloseSocket(socket);
            return response;
        } catch (Exception e) {
            System.out.println("[Executor] CoverageManager: sendCommand: Exception: " + e.getMessage());

            // Server is down or not responding. Disable coverage manager.
            if (isEnabled) {
                System.out.println("[Executor] CoverageManager: sendCommand: Server is down or not responding. Disable coverage manager.");
                isEnabled = false;
            }
            TryCloseSocket(socket);
            return null;
        }
    }

    private String sendPing(boolean tryIfDisabled) {
        Map<String, String> payload = new HashMap<>();
        payload.put("command", "ping");
        payload.put("harness_id", harnessId);
        payload.put("java_home", javaHome);
        String jsonPayload = new Gson().toJson(payload);
        return sendCommand(jsonPayload, tryIfDisabled);
    }

    private String sendPing() {
        return sendPing(false);
    }

    public void addTriedBranches(List<String> branches) {
        AddTriedBranchesPayload payload = new AddTriedBranchesPayload(branches);
        String jsonPayload = new Gson().toJson(payload);
        sendCommand(jsonPayload);
    }

    public void updateSeed(String seed_path, List<String> classes) {
        UpdateSeedPayload payload = new UpdateSeedPayload(seed_path, classes);
        String jsonPayload = new Gson().toJson(payload);
        sendCommand(jsonPayload);
    }

    public List<String> getPartlyVisitedBranches() {
        GetPartlyVisitedBranchesPayload payload = new GetPartlyVisitedBranchesPayload();
        String jsonPayload = new Gson().toJson(payload);
        String response = sendCommand(jsonPayload);
        if (response == null) {
            return new ArrayList<>();
        }
        List<String> responseList = new Gson().fromJson(response, List.class);
        return responseList;
    }

    private boolean initEnabled() {
        if (harnessId == null || javaHome == null) {
            return false;
        }

        // check if the port is open
        String response = sendPing(true);
        if (response == null) {
            System.out.println("[Executor] CoverageManager: checkEnabled: sendPing failed");
            return false;
        }
        Map<String, String> responseMap = new Gson().fromJson(response, Map.class);
        if (responseMap.get("status").equals("ok")) {
            System.out.println("[Executor] CoverageManager: checkEnabled: ok");
            return true;
        }
        return false;
    }

    public boolean isEnabled() {
        if (portNumber <= 0) {
            return false;
        }
        return isEnabled;
    }
}
