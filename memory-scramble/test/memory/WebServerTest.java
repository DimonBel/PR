/* Copyright (c) 2017-2020 MIT 6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */
package memory;

import static java.nio.charset.StandardCharsets.UTF_8;
import static org.junit.jupiter.api.Assertions.*;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

public class WebServerTest {
    @Test
    public void testAssertionsEnabled() {
        assertThrows(AssertionError.class, () -> {
            assert false;
        }, "make sure assertions are enabled with VM argument '-ea'");
    }

    @Test
    public void helloEndpointReturnsGreeting() throws IOException {
        Board board = boardFromSymbols(1, 1, "A");
        WebServer server = new WebServer(board, 0);
        server.start();
        try {
            URL url = urlFor(server, "/hello/world");
            List<String> lines = readAllLines(url);
            assertEquals(List.of("Hello, world!"), lines);
        } finally {
            server.stop();
        }
    }

    @Test
    public void helloEndpointRejectsInvalidName() throws IOException {
        Board board = boardFromSymbols(1, 1, "A");
        WebServer server = new WebServer(board, 0);
        server.start();
        try {
            URL url = urlFor(server, "/hello/world!");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            assertEquals(404, connection.getResponseCode());
        } finally {
            server.stop();
        }
    }

    @Test
    public void flipEndpointReturnsUpdatedView() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        WebServer server = new WebServer(board, 0);
        server.start();
        try {
            URL url = urlFor(server, "/flip/Alice/0,0");
            List<String> lines = readAllLines(url);
            assertEquals("2x2", lines.get(0));
            assertEquals("my A", lines.get(1));
        } finally {
            server.stop();
        }
    }

    @Test
    public void lookEndpointReflectsBoardState() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        WebServer server = new WebServer(board, 0);
        server.start();
        try {
            urlFor(server, "/flip/Alice/0,0").openStream().close();
            URL url = urlFor(server, "/look/Alice");
            List<String> lines = readAllLines(url);
            assertTrue(lines.contains("my A"));
        } finally {
            server.stop();
        }
    }

    @Test
    public void replaceEndpointReplacesSymbols() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        WebServer server = new WebServer(board, 0);
        server.start();
        try {
            String encodedOld = URLEncoder.encode("A", UTF_8);
            String encodedNew = URLEncoder.encode("🚗", UTF_8);
            URL url = urlFor(server, "/replace/alice/" + encodedOld + "/" + encodedNew);
            readAllLines(url);
            assertEquals("🚗", board.getCard(0, 0).getSymbol());
            assertEquals("🚗", board.getCard(1, 0).getSymbol());
        } finally {
            server.stop();
        }
    }

    private List<String> readAllLines(URL url) throws IOException {
        List<String> lines = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(url.openStream(), UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                lines.add(line);
            }
        }
        return lines;
    }

    private Board boardFromSymbols(int rows, int cols, String... symbols) throws IOException {
        List<String> lines = new ArrayList<>();
        lines.add(rows + "x" + cols);
        for (String symbol : symbols) {
            lines.add(symbol);
        }
        Path temp = Files.createTempFile("web-board", ".txt");
        Files.write(temp, lines);
        Board board = Board.parseFromFile(temp.toString());
        Files.deleteIfExists(temp);
        return board;
    }

    private URL urlFor(WebServer server, String path) throws IOException {
        String normalized = path.startsWith("/") ? path : "/" + path;
        try {
            return new URI("http", null, "localhost", server.port(), normalized, null, null).toURL();
        } catch (Exception e) {
            if (e instanceof IOException io) {
                throw io;
            }
            throw new IOException(e);
        }
    }
}
