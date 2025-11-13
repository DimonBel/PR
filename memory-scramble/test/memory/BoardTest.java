/* Copyright (c) 2017-2020 MIT 6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */
package memory;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.junit.jupiter.api.Test;

public class BoardTest {
    @Test
    public void testAssertionsEnabled() {
        assertThrows(AssertionError.class, () -> {
            assert false;
        }, "make sure assertions are enabled with VM argument '-ea'");
    }

    @Test
    public void parseFromFileReadsDimensions() throws IOException {
        Board board = boardFromSymbols(1, 1, "A");
        assertEquals("1x1", board.toString().trim().split("\n")[0]);
    }

    @Test
    public void parseFromFileParsesEmojiBoard() throws IOException {
        Board board = Board.parseFromFile("boards/perfect.txt");
        assertEquals("3x3", board.toString().trim().split("\n")[0]);
    }

    @Test
    public void parseFromFileParsesLargerBoard() throws IOException {
        Board board = Board.parseFromFile("boards/ab.txt");
        assertTrue(board.toString().startsWith("5x5"));
    }

    @Test
    public void parseFromFileRejectsWrongCardCount() throws IOException {
        Path file = writeTempFile("2x2\nA\nB\nC\n");
        try {
            assertThrows(AssertionError.class, () -> Board.parseFromFile(file.toString()));
        } finally {
            Files.deleteIfExists(file);
        }
    }

    @Test
    public void parseFromFileRejectsInvalidDimensions() throws IOException {
        Path file = writeTempFile("0x0\n");
        try {
            assertThrows(AssertionError.class, () -> Board.parseFromFile(file.toString()));
        } finally {
            Files.deleteIfExists(file);
        }
    }

    @Test
    public void parseFromFileRejectsMalformedHeader() throws IOException {
        Path file = writeTempFile("not-a-board\nA\n");
        try {
            assertThrows(IllegalStateException.class, () -> Board.parseFromFile(file.toString()));
        } finally {
            Files.deleteIfExists(file);
        }
    }

    @Test
    public void lookShowsAllCardsFaceDownInitially() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        Player alice = board.getPlayer("alice");
        String[] lines = board.viewBy(alice).split("\n");

        assertEquals("2x2", lines[0]);
        for (int i = 1; i < lines.length; i++) {
            if (!lines[i].isEmpty()) {
                assertEquals("down", lines[i]);
            }
        }
    }

    @Test
    public void flipFirstCardShowsAsControlled() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        Player alice = board.getPlayer("alice");

        board.turn(alice, 0, 0);
        String[] lines = board.viewBy(alice).split("\n");

        assertEquals("my A", lines[1]);
    }

    @Test
    public void secondPlayerCanClaimFaceUpUncontrolledCard() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        board.registerPlayer("bob");
        Player alice = board.getPlayer("alice");
        Player bob = board.getPlayer("bob");

        board.turn(alice, 0, 0);
        board.turn(alice, 0, 1); // non-match leaves cards face up but uncontrolled

        board.turn(bob, 0, 0);
        String[] bobView = board.viewBy(bob).split("\n");
        assertEquals("my A", bobView[1]);
    }

    @Test
    public void nonMatchingSecondCardRelinquishesControl() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        Player alice = board.getPlayer("alice");

        board.turn(alice, 0, 0);
        board.turn(alice, 0, 1);

        String[] lines = board.viewBy(alice).split("\n");
        assertEquals("up A", lines[1]);
        assertEquals("up B", lines[2]);
    }

    @Test
    public void flipWaitsForControlledCard() throws Exception {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        board.registerPlayer("bob");
        Player alice = board.getPlayer("alice");
        Player bob = board.getPlayer("bob");

        board.turn(alice, 0, 0);

        CountDownLatch started = new CountDownLatch(1);
        CompletableFuture<Void> bobTurn = CompletableFuture.runAsync(() -> {
            started.countDown();
            board.turn(bob, 0, 0);
        });

        assertTrue(started.await(200, TimeUnit.MILLISECONDS));
        assertFalse(bobTurn.isDone());

        board.turn(alice, 0, 1); // relinquishes the first card
        bobTurn.get(2, TimeUnit.SECONDS);
        assertTrue(board.viewBy(bob).contains("my A"));
    }

    @Test
    public void matchingCardsAreRemovedOnNextMove() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        Player alice = board.getPlayer("alice");

        board.turn(alice, 0, 0);
        board.turn(alice, 1, 0);
        board.turn(alice, 0, 1); // triggers removal of previous match

        String[] lines = board.viewBy(alice).split("\n");
        assertEquals("none", lines[1]);
        assertEquals("none", lines[3]);
        assertTrue(alice.getScore() >= 1);
    }

    @Test
    public void otherPlayersSeeUpNotMy() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        board.registerPlayer("bob");
        Player alice = board.getPlayer("alice");
        Player bob = board.getPlayer("bob");

        board.turn(alice, 0, 0);
        String[] bobLines = board.viewBy(bob).split("\n");
        assertEquals("up A", bobLines[1]);
    }

    @Test
    public void replaceSymbolsUpdatesAllMatchingCards() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.replaceSymbols("alice", "A", "X");

        assertEquals("X", board.getCard(0, 0).getSymbol());
        assertEquals("X", board.getCard(1, 0).getSymbol());
    }

    @Test
    public void replaceSymbolsKeepsFaceStateAndControl() throws IOException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("alice");
        Player alice = board.getPlayer("alice");

        board.turn(alice, 0, 0);
        String before = board.viewBy(alice);
        assertTrue(before.contains("my A"));

        board.replaceSymbols("alice", "A", "X");
        assertEquals("X", board.getCard(0, 0).getSymbol());
        String afterView = board.viewBy(alice);
        assertTrue(afterView.contains("my X"));
    }

    @Test
    public void replaceSymbolsNotifiesWatchers()
            throws IOException, InterruptedException, ExecutionException, TimeoutException {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("watcher");
        Player watcher = board.getPlayer("watcher");

        CountDownLatch ready = new CountDownLatch(1);
        CompletableFuture<String> watchFuture = new CompletableFuture<>();
        Thread watcherThread = new Thread(() -> {
            ready.countDown();
            try {
                watchFuture.complete(board.watch(watcher));
            } catch (Exception e) {
                watchFuture.completeExceptionally(e);
            }
        });
        watcherThread.setDaemon(true);
        watcherThread.start();

        assertTrue(ready.await(1, TimeUnit.SECONDS));
        board.replaceSymbols("alice", "B", "Y");
        watchFuture.get(2, TimeUnit.SECONDS);
        assertEquals("Y", board.getCard(0, 1).getSymbol());
        assertEquals("Y", board.getCard(1, 1).getSymbol());
    }

    @Test
    public void watchNotifiedOnFlip() throws Exception {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("watcher");
        board.registerPlayer("alice");
        Player watcher = board.getPlayer("watcher");
        Player alice = board.getPlayer("alice");

        CompletableFuture<String> watchFuture = CompletableFuture.supplyAsync(() -> board.watch(watcher));

        Thread.sleep(50); // allow watcher to block
        board.turn(alice, 0, 0);

        String view = watchFuture.get(2, TimeUnit.SECONDS);
        assertTrue(view.contains("up A"));
    }

    @Test
    public void multipleWatchersAreAllNotified() throws Exception {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("watcher1");
        board.registerPlayer("watcher2");
        board.registerPlayer("alice");
        Player watcher1 = board.getPlayer("watcher1");
        Player watcher2 = board.getPlayer("watcher2");
        Player alice = board.getPlayer("alice");

        CompletableFuture<String> first = CompletableFuture.supplyAsync(() -> board.watch(watcher1));
        CompletableFuture<String> second = CompletableFuture.supplyAsync(() -> board.watch(watcher2));

        Thread.sleep(50);
        board.turn(alice, 0, 0);

        String firstView = first.get(2, TimeUnit.SECONDS);
        String secondView = second.get(2, TimeUnit.SECONDS);
        assertTrue(firstView.contains("up A"));
        assertTrue(secondView.contains("up A"));
    }

    @Test
    public void concurrentTurnsAllowDifferentPlayers() throws IOException, InterruptedException {
        Board board = boardFromSymbols(3, 3, "A", "B", "C", "A", "B", "C", "D", "D", "E");
        board.registerPlayer("alice");
        board.registerPlayer("bob");
        Player alice = board.getPlayer("alice");
        Player bob = board.getPlayer("bob");

        Thread t1 = new Thread(() -> board.turn(alice, 0, 0));
        Thread t2 = new Thread(() -> board.turn(bob, 0, 1));
        t1.start();
        t2.start();
        t1.join();
        t2.join();

        String aliceView = board.viewBy(alice);
        String bobView = board.viewBy(bob);

        assertTrue(aliceView.contains("my A"));
        assertTrue(bobView.contains("my B"));
    }

    @Test
    public void multipleWaitersOnlyOneSucceeds() throws Exception {
        Board board = boardFromSymbols(2, 2, "A", "B", "A", "B");
        board.registerPlayer("owner");
        board.registerPlayer("waiter1");
        board.registerPlayer("waiter2");
        Player owner = board.getPlayer("owner");
        Player waiter1 = board.getPlayer("waiter1");
        Player waiter2 = board.getPlayer("waiter2");

        board.turn(owner, 0, 0);

        CountDownLatch started = new CountDownLatch(2);
        CompletableFuture<Void> wait1 = CompletableFuture.runAsync(() -> {
            started.countDown();
            board.turn(waiter1, 0, 0);
        });
        CompletableFuture<Void> wait2 = CompletableFuture.runAsync(() -> {
            started.countDown();
            board.turn(waiter2, 0, 0);
        });

        assertTrue(started.await(200, TimeUnit.MILLISECONDS));
        board.turn(owner, 0, 1);

        CompletableFuture.anyOf(wait1, wait2).get(2, TimeUnit.SECONDS);
        Thread.sleep(50);

        String view1 = board.viewBy(waiter1);
        String view2 = board.viewBy(waiter2);
        boolean waiter1Owns = view1.contains("my A");
        boolean waiter2Owns = view2.contains("my A");
        assertTrue(waiter1Owns ^ waiter2Owns, "Exactly one waiter should control the card");

        wait1.cancel(true);
        wait2.cancel(true);
    }

    private Path writeTempFile(String contents) throws IOException {
        Path file = Files.createTempFile("board-input", ".txt");
        Files.writeString(file, contents);
        return file;
    }

    private Board boardFromSymbols(int rows, int cols, String... symbols) throws IOException {
        List<String> lines = new ArrayList<>();
        lines.add(rows + "x" + cols);
        for (String symbol : symbols) {
            lines.add(symbol);
        }
        Path temp = Files.createTempFile("board", ".txt");
        Files.write(temp, lines);
        Board board = Board.parseFromFile(temp.toString());
        Files.deleteIfExists(temp);
        return board;
    }
}
