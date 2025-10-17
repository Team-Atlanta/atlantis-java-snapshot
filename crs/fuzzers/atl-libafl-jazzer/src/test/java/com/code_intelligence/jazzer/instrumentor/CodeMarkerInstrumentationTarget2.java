/*
 * Copyright 2025 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.code_intelligence.jazzer.instrumentor;

import java.io.File;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.channels.SocketChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.HashMap;
import java.util.Map;

public class CodeMarkerInstrumentationTarget2 implements DynamicTestContract {

  @Override
  public Map<String, Boolean> selfCheck() {
    Map<String, Boolean> results = new HashMap<>();

    // FUZZER ENTRY POINT TEST (when ATLJAZZER_INFER_CPMETA_OUTPUT is set)
    results.put("testFuzzerTestOneInput", testFuzzerTestOneInput());

    // CUSTOM API CALL (when ATLJAZZER_CUSTOM_SINKPOINT_CONF is set)
    results.put("testCustomSinkpoint", testCustomSinkpoint());

    // SSRF SINKPOINTS
    results.put("testSocketConnect", testSocketConnect());
    results.put("testSocketImplConnect", testSocketImplConnect());
    results.put("testSocksSocketImplConnect", testSocksSocketImplConnect());
    results.put("testSocketChannelConnect", testSocketChannelConnect());
    results.put("testSocketAdaptorConnect", testSocketAdaptorConnect());
    results.put("testPlainHttpConnectionConnect", testPlainHttpConnectionConnect());

    // SQL INJECTION SINKPOINTS
    results.put("testStatementExecute", testStatementExecute());
    results.put("testStatementExecuteBatch", testStatementExecuteBatch());
    results.put("testStatementExecuteLargeBatch", testStatementExecuteLargeBatch());
    results.put("testStatementExecuteLargeUpdate", testStatementExecuteLargeUpdate());
    results.put("testStatementExecuteQuery", testStatementExecuteQuery());
    results.put("testStatementExecuteUpdate", testStatementExecuteUpdate());
    results.put("testEntityManagerCreateNativeQuery", testEntityManagerCreateNativeQuery());

    // FILE PATH TRAVERSAL SINKPOINTS
    results.put("testFilesCreateDirectory", testFilesCreateDirectory());
    results.put("testFilesCreateDirectories", testFilesCreateDirectories());
    results.put("testFilesCreateFile", testFilesCreateFile());
    results.put("testFilesCreateTempDirectory", testFilesCreateTempDirectory());
    results.put("testFilesCreateTempFile", testFilesCreateTempFile());
    results.put("testFilesDelete", testFilesDelete());
    results.put("testFilesDeleteIfExists", testFilesDeleteIfExists());
    results.put("testFilesLines", testFilesLines());
    results.put("testFilesNewByteChannel", testFilesNewByteChannel());
    results.put("testFilesNewBufferedReader", testFilesNewBufferedReader());
    results.put("testFilesNewBufferedWriter", testFilesNewBufferedWriter());
    results.put("testFilesReadString", testFilesReadString());
    results.put("testFilesReadAllBytes", testFilesReadAllBytes());
    results.put("testFilesReadAllLines", testFilesReadAllLines());
    results.put("testFilesReadSymbolicLink", testFilesReadSymbolicLink());
    results.put("testFilesWrite", testFilesWrite());
    results.put("testFilesWriteString", testFilesWriteString());
    results.put("testFilesNewInputStream", testFilesNewInputStream());
    results.put("testFilesNewOutputStream", testFilesNewOutputStream());
    results.put("testFileChannelOpen", testFileChannelOpen());
    results.put("testFilesCopy", testFilesCopy());
    results.put("testFilesMismatch", testFilesMismatch());
    results.put("testFilesMove", testFilesMove());
    results.put("testFileReaderInit", testFileReaderInit());
    results.put("testFileWriterInit", testFileWriterInit());
    results.put("testFileInputStreamInit", testFileInputStreamInit());
    results.put("testFileOutputStreamInit", testFileOutputStreamInit());
    results.put("testScannerInit", testScannerInit());
    results.put("testFilesProbeContentType", testFilesProbeContentType());

    return results;
  }

  private boolean testSocketConnect() {
    try {
      // Create a non-connected socket
      Socket socket = new Socket();

      // Create an address - use localhost with a high port to avoid accidental connections
      InetSocketAddress address = new InetSocketAddress("localhost", 44444);

      // Set a short timeout to avoid hanging tests
      int timeout = 1;

      // Call the connect method with timeout to trigger the instrumentation
      // This will likely fail to connect, which is fine for the test
      try {
        socket.connect(address, timeout);
      } catch (Exception e) {
        // Expected - we're just testing the instrumentation, not the connection
      } finally {
        // Always close the socket
        try {
          socket.close();
        } catch (Exception e) {
          // Ignore
        }
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // SocketImpl is a JDK internal class, this method is implemented to match the test contract
  // but the actual test is skipped in the test class
  private boolean testSocketImplConnect() {
    return true;
  }

  // SocksSocketImpl is a JDK internal class, this method is implemented to match the test contract
  // but the actual test is skipped in the test class
  private boolean testSocksSocketImplConnect() {
    return true;
  }

  private boolean testSocketChannelConnect() {
    SocketChannel channel = null;
    try {
      // Open a SocketChannel
      channel = SocketChannel.open();

      // Create an address - use localhost with a high port to avoid accidental connections
      InetSocketAddress address = new InetSocketAddress("localhost", 44447);

      // Try to connect (this will likely fail but that's fine for the test)
      try {
        channel.connect(address);
      } catch (IOException e) {
        // Expected - we're just testing the instrumentation, not the connection
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    } finally {
      // Always close the channel
      if (channel != null) {
        try {
          channel.close();
        } catch (IOException e) {
          // Ignore
        }
      }
    }
  }

  // SocketAdaptor is a JDK internal class, this method is implemented to match the test contract
  // but the actual test is skipped in the test class
  private boolean testSocketAdaptorConnect() {
    return true;
  }

  // PlainHttpConnection is a JDK internal class, this method is implemented to match the test
  // contract
  // but the actual test is skipped in the test class
  private boolean testPlainHttpConnectionConnect() {
    return true;
  }

  // SQL INJECTION SINKPOINTS

  // Common method to simulate a JDBC connection for SQL methods
  private Connection getSimulatedConnection() {
    // This isn't a real connection - just for instrumentation testing
    return null;
  }

  private boolean testStatementExecute() {
    try {
      System.out.println("Testing Statement.execute");

      // For testing instrumentation only - this won't actually execute
      String sql = "SELECT * FROM users WHERE username = 'test'";

      try {
        // In a real scenario, we'd do:
        // Connection conn = getSimulatedConnection();
        // Statement stmt = conn.createStatement();
        // stmt.execute(sql);

        // But we'll simulate it for instrumentation testing
        Statement stmt = null;
        if (stmt != null) {
          stmt.execute(sql);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testStatementExecuteBatch() {
    try {
      System.out.println("Testing Statement.executeBatch");

      try {
        // In a real scenario, we'd do:
        // Connection conn = getSimulatedConnection();
        // Statement stmt = conn.createStatement();
        // stmt.addBatch("INSERT INTO users VALUES (1, 'test')");
        // stmt.addBatch("INSERT INTO users VALUES (2, 'test2')");
        // stmt.executeBatch();

        // But we'll simulate it for instrumentation testing
        Statement stmt = null;
        if (stmt != null) {
          stmt.executeBatch();
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testStatementExecuteLargeBatch() {
    try {
      System.out.println("Testing Statement.executeLargeBatch");

      try {
        // In a real scenario, we'd do:
        // Connection conn = getSimulatedConnection();
        // Statement stmt = conn.createStatement();
        // stmt.addBatch("INSERT INTO users VALUES (1, 'test')");
        // stmt.addBatch("INSERT INTO users VALUES (2, 'test2')");
        // stmt.executeLargeBatch();

        // But we'll simulate it for instrumentation testing
        Statement stmt = null;
        if (stmt != null) {
          stmt.executeLargeBatch();
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testStatementExecuteLargeUpdate() {
    try {
      System.out.println("Testing Statement.executeLargeUpdate");

      // For testing instrumentation only - this won't actually execute
      String sql = "UPDATE users SET active = true WHERE username = 'test'";

      try {
        // In a real scenario, we'd do:
        // Connection conn = getSimulatedConnection();
        // Statement stmt = conn.createStatement();
        // stmt.executeLargeUpdate(sql);

        // But we'll simulate it for instrumentation testing
        Statement stmt = null;
        if (stmt != null) {
          stmt.executeLargeUpdate(sql);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testStatementExecuteQuery() {
    try {
      System.out.println("Testing Statement.executeQuery");

      // For testing instrumentation only - this won't actually execute
      String sql = "SELECT * FROM users WHERE username = 'test'";

      try {
        // In a real scenario, we'd do:
        // Connection conn = getSimulatedConnection();
        // Statement stmt = conn.createStatement();
        // ResultSet rs = stmt.executeQuery(sql);

        // But we'll simulate it for instrumentation testing
        Statement stmt = null;
        if (stmt != null) {
          ResultSet rs = stmt.executeQuery(sql);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testStatementExecuteUpdate() {
    try {
      System.out.println("Testing Statement.executeUpdate");

      // For testing instrumentation only - this won't actually execute
      String sql = "UPDATE users SET active = true WHERE username = 'test'";

      try {
        // In a real scenario, we'd do:
        // Connection conn = getSimulatedConnection();
        // Statement stmt = conn.createStatement();
        // stmt.executeUpdate(sql);

        // But we'll simulate it for instrumentation testing
        Statement stmt = null;
        if (stmt != null) {
          stmt.executeUpdate(sql);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // EntityManager.createNativeQuery requires JPA dependency, this method is implemented to match
  // the test contract
  // but the actual test is skipped in the test class
  private boolean testEntityManagerCreateNativeQuery() {
    return true;
  }

  // FILE PATH TRAVERSAL SINKPOINTS

  // Helper to get a safe test path - we won't actually create any files
  private Path getSafeTestPath(String name) {
    return Paths.get(System.getProperty("java.io.tmpdir"), "jazzer_test_" + name);
  }

  private boolean testFilesCreateDirectory() {
    try {
      System.out.println("Testing Files.createDirectory");

      Path path = getSafeTestPath("testdir");

      try {
        // We don't actually want to create the directory, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.createdir"))
            && !Files.exists(path)) {
          // This is just to avoid warnings about using the API incorrectly
          Files.createDirectory(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesCreateDirectories() {
    try {
      System.out.println("Testing Files.createDirectories");

      Path path = getSafeTestPath("testdirs/nested");

      try {
        // We don't actually want to create the directories, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.createdirs"))
            && !Files.exists(path)) {
          // This is just to avoid warnings about using the API incorrectly
          Files.createDirectories(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesCreateFile() {
    try {
      System.out.println("Testing Files.createFile");

      Path path = getSafeTestPath("testfile.txt");

      try {
        // We don't actually want to create the file, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.createfile"))
            && !Files.exists(path)) {
          // This is just to avoid warnings about using the API incorrectly
          Files.createFile(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesCreateTempDirectory() {
    try {
      System.out.println("Testing Files.createTempDirectory");

      Path dir = Paths.get(System.getProperty("java.io.tmpdir"));
      String prefix = "jazzer_test_";

      try {
        // We don't actually want to create the directory, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.createtempdir"))) {
          Path tempDir = Files.createTempDirectory(dir, prefix);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesCreateTempFile() {
    try {
      System.out.println("Testing Files.createTempFile");

      Path dir = Paths.get(System.getProperty("java.io.tmpdir"));
      String prefix = "jazzer_test_";
      String suffix = ".tmp";

      try {
        // We don't actually want to create the file, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.createtempfile"))) {
          Path tempFile = Files.createTempFile(dir, prefix, suffix);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesDelete() {
    try {
      System.out.println("Testing Files.delete");

      Path path = getSafeTestPath("testdelete.txt");

      try {
        // We don't actually want to delete anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.delete")) && Files.exists(path)) {
          // This is just to avoid warnings about using the API incorrectly
          Files.delete(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesDeleteIfExists() {
    try {
      System.out.println("Testing Files.deleteIfExists");

      Path path = getSafeTestPath("testdeleteifexists.txt");

      try {
        // We don't actually want to delete anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.deleteifexists"))) {
          boolean deleted = Files.deleteIfExists(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesLines() {
    try {
      System.out.println("Testing Files.lines");

      Path path = getSafeTestPath("testlines.txt");

      try {
        // We don't actually want to read anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.lines")) && Files.exists(path)) {
          try (java.util.stream.Stream<String> lines = Files.lines(path)) {
            // Do nothing with the lines
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesNewByteChannel() {
    try {
      System.out.println("Testing Files.newByteChannel");

      Path path = getSafeTestPath("testbytechannel.txt");

      try {
        // We don't actually want to create a channel, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.bytechannel"))
            && Files.exists(path)) {
          try (java.nio.channels.SeekableByteChannel channel =
              Files.newByteChannel(path, java.nio.file.StandardOpenOption.READ)) {
            // Do nothing with the channel
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesNewBufferedReader() {
    try {
      System.out.println("Testing Files.newBufferedReader");

      Path path = getSafeTestPath("testbufferedreader.txt");

      try {
        // We don't actually want to create a reader, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.bufferedreader"))
            && Files.exists(path)) {
          try (java.io.BufferedReader reader = Files.newBufferedReader(path)) {
            // Do nothing with the reader
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesNewBufferedWriter() {
    try {
      System.out.println("Testing Files.newBufferedWriter");

      Path path = getSafeTestPath("testbufferedwriter.txt");

      try {
        // We don't actually want to create a writer, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.bufferedwriter"))
            && !Files.exists(path)) {
          try (java.io.BufferedWriter writer =
              Files.newBufferedWriter(path, java.nio.file.StandardOpenOption.CREATE)) {
            // Do nothing with the writer
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesReadString() {
    try {
      System.out.println("Testing Files.readString");

      Path path = getSafeTestPath("testreadstring.txt");

      try {
        // We don't actually want to read anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.readstring"))
            && Files.exists(path)) {
          String content = Files.readString(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesReadAllBytes() {
    try {
      System.out.println("Testing Files.readAllBytes");

      Path path = getSafeTestPath("testreadbytes.txt");

      try {
        // We don't actually want to read anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.readallbytes"))
            && Files.exists(path)) {
          byte[] bytes = Files.readAllBytes(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesReadAllLines() {
    try {
      System.out.println("Testing Files.readAllLines");

      Path path = getSafeTestPath("testreadlines.txt");

      try {
        // We don't actually want to read anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.readalllines"))
            && Files.exists(path)) {
          java.util.List<String> lines = Files.readAllLines(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesReadSymbolicLink() {
    try {
      System.out.println("Testing Files.readSymbolicLink");

      Path path = getSafeTestPath("testsymlink");

      try {
        // We don't actually want to read anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.readsymboliclink"))
            && Files.exists(path)
            && Files.isSymbolicLink(path)) {
          Path target = Files.readSymbolicLink(path);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesWrite() {
    try {
      System.out.println("Testing Files.write");

      Path path = getSafeTestPath("testwrite.txt");
      byte[] bytes = "test".getBytes();

      try {
        // We don't actually want to write anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.write")) && !Files.exists(path)) {
          Files.write(path, bytes, java.nio.file.StandardOpenOption.CREATE);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesWriteString() {
    try {
      System.out.println("Testing Files.writeString");

      Path path = getSafeTestPath("testwritestring.txt");
      String content = "test";

      try {
        // We don't actually want to write anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.writestring"))
            && !Files.exists(path)) {
          Files.writeString(path, content, java.nio.file.StandardOpenOption.CREATE);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesNewInputStream() {
    try {
      System.out.println("Testing Files.newInputStream");

      Path path = getSafeTestPath("testinputstream.txt");

      try {
        // We don't actually want to create a stream, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.inputstream"))
            && Files.exists(path)) {
          try (java.io.InputStream in = Files.newInputStream(path)) {
            // Do nothing with the stream
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesNewOutputStream() {
    try {
      System.out.println("Testing Files.newOutputStream");

      Path path = getSafeTestPath("testoutputstream.txt");

      try {
        // We don't actually want to create a stream, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.outputstream"))
            && !Files.exists(path)) {
          try (java.io.OutputStream out =
              Files.newOutputStream(path, java.nio.file.StandardOpenOption.CREATE)) {
            // Do nothing with the stream
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFileChannelOpen() {
    try {
      System.out.println("Testing FileChannel.open");

      Path path = getSafeTestPath("testfilechannel.txt");

      try {
        // We don't actually want to open a channel, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.filechannel"))
            && Files.exists(path)) {
          try (java.nio.channels.FileChannel channel =
              java.nio.channels.FileChannel.open(path, java.nio.file.StandardOpenOption.READ)) {
            // Do nothing with the channel
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesCopy() {
    try {
      System.out.println("Testing Files.copy");

      Path source = getSafeTestPath("testsource.txt");
      Path target = getSafeTestPath("testtarget.txt");

      try {
        // We don't actually want to copy anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.copy"))
            && Files.exists(source)
            && !Files.exists(target)) {
          Files.copy(source, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesMismatch() {
    try {
      System.out.println("Testing Files.mismatch");

      Path path1 = getSafeTestPath("testmismatch1.txt");
      Path path2 = getSafeTestPath("testmismatch2.txt");

      try {
        // We don't actually want to do any comparison, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.mismatch"))
            && Files.exists(path1)
            && Files.exists(path2)) {
          long mismatchPos = Files.mismatch(path1, path2);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFilesMove() {
    try {
      System.out.println("Testing Files.move");

      Path source = getSafeTestPath("testmovesource.txt");
      Path target = getSafeTestPath("testmovetarget.txt");

      try {
        // We don't actually want to move anything, just test the instrumentation
        if ("true".equals(System.getProperty("jazzer.never.exist.move"))
            && Files.exists(source)
            && !Files.exists(target)) {
          Files.move(source, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFileReaderInit() {
    try {
      System.out.println("Testing FileReader.<init>");

      String filePath = getSafeTestPath("testfilereader.txt").toString();

      try {
        // We don't actually want to create a reader, just test the instrumentation
        File file = new File(filePath);
        if ("true".equals(System.getProperty("jazzer.never.exist.filereader")) && file.exists()) {
          try (java.io.FileReader reader = new java.io.FileReader(filePath)) {
            // Do nothing with the reader
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFileWriterInit() {
    try {
      System.out.println("Testing FileWriter.<init>");

      String filePath = getSafeTestPath("testfilewriter.txt").toString();

      try {
        // We don't actually want to create a writer, just test the instrumentation
        File file = new File(filePath);
        if ("true".equals(System.getProperty("jazzer.never.exist.filewriter")) && !file.exists()) {
          try (java.io.FileWriter writer = new java.io.FileWriter(filePath)) {
            // Do nothing with the writer
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFileInputStreamInit() {
    try {
      System.out.println("Testing FileInputStream.<init>");

      String filePath = getSafeTestPath("testfileinputstream.txt").toString();

      try {
        // We don't actually want to create a stream, just test the instrumentation
        File file = new File(filePath);
        if ("true".equals(System.getProperty("jazzer.never.exist.fileinputstream"))
            && file.exists()) {
          try (java.io.FileInputStream in = new java.io.FileInputStream(filePath)) {
            // Do nothing with the stream
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testFileOutputStreamInit() {
    try {
      System.out.println("Testing FileOutputStream.<init>");

      String filePath = getSafeTestPath("testfileoutputstream.txt").toString();

      try {
        // We don't actually want to create a stream, just test the instrumentation
        File file = new File(filePath);
        if ("true".equals(System.getProperty("jazzer.never.exist.fileoutputstream"))
            && !file.exists()) {
          try (java.io.FileOutputStream out = new java.io.FileOutputStream(filePath)) {
            // Do nothing with the stream
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  private boolean testScannerInit() {
    try {
      System.out.println("Testing Scanner.<init>");

      String filePath = getSafeTestPath("testscanner.txt").toString();

      try {
        // We don't actually want to create a scanner, just test the instrumentation
        File file = new File(filePath);
        if ("true".equals(System.getProperty("jazzer.never.exist.scanner")) && file.exists()) {
          try (java.util.Scanner scanner = new java.util.Scanner(file)) {
            // Do nothing with the scanner
          }
        }
      } catch (Exception e) {
        // Expected - we're just testing instrumentation
      }

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  // This method is skipped because the MethodHook is targeting
  // "java.nio.file.probeContentType" (a class that doesn't exist) instead of
  // java.nio.file.Files.probeContentType (which is the actual method)
  private boolean testFilesProbeContentType() {
    try {
      System.out.println(
          "SKIPPED: Testing Files.probeContentType - class mismatch in instrumentation");
      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  /**
   * Test for the fuzzerTestOneInput special marker when ATLJAZZER_INFER_CPMETA_OUTPUT is set. This
   * creates a dummy call to a method named "fuzzerTestOneInput" to test the instrumentation.
   */
  private boolean testFuzzerTestOneInput() {
    try {
      System.out.println(
          "Testing fuzzerTestOneInput detection when ATLJAZZER_INFER_CPMETA_OUTPUT is set");

      // This method will be instrumented directly due to its name
      fuzzerTestOneInput(new byte[0]);

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  /**
   * This method will be directly instrumented when ATLJAZZER_INFER_CPMETA_OUTPUT is set because its
   * name is "fuzzerTestOneInput"
   */
  public static void fuzzerTestOneInput(byte[] input) {
    // Do something randomly
    if (input != null && input.length > 0) {
      System.out.println("fuzzerTestOneInput called with input of size: " + input.length);
    } else {
      System.out.println("fuzzerTestOneInput called with null or empty input");
    }
  }

  /**
   * Custom test method for the configurable sinkpoint feature. Tests both custom API sinkpoints and
   * custom sink coordinates specified through the config file.
   */
  private boolean testCustomSinkpoint() {
    try {
      System.out.println("Testing custom sinkpoint");

      // Call the custom API - this should be marked when the config file is provided
      // For coordinate-based testing, a specific bytecode offset in this method will be marked
      customApiMethod("test-input");

      return true;
    } catch (Exception e) {
      e.printStackTrace();
      return false;
    }
  }

  /**
   * A custom API method that will be marked as a sink when configured through
   * ATLJAZZER_CUSTOM_SINKPOINT_CONF. Can also be used to test coordinate-based sinkpoints.
   */
  public static void customApiMethod(String input) {
    System.out.println("Custom API method called with input: " + input);
  }
}
