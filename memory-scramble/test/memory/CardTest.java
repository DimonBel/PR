package memory;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

public class CardTest {
    @Test
    public void testAssertionsEnabled() {
        assertThrows(AssertionError.class, () -> {
            assert false;
        }, "make sure assertions are enabled with VM argument '-ea'");
    }

    @Test
    public void cardStoresInitialSymbol() {
        Card card = new Card("A");
        assertEquals("A", card.getSymbol());
        assertFalse(card.isUp());
        assertFalse(card.isControlled());
        assertFalse(card.isEmpty());
    }

    @Test
    public void setOwnerAndRelinquishControl() throws EmptyCardException {
        Card card = new Card("A");
        Player player = new Player("alice");
        Object notifier = new Object();

        player.turnOver(card, notifier);
        assertEquals(player, card.getOwner());
        assertTrue(card.isControlled());
        assertTrue(card.isUp());

        card.relinquish();
        assertFalse(card.isControlled());
        assertNull(card.getOwner());
    }

    @Test
    public void viewByReflectsPerspective() throws EmptyCardException {
        Card card = new Card("A");
        Player owner = new Player("owner");
        Player observer = new Player("observer");
        Object notifier = new Object();

        owner.turnOver(card, notifier);
        assertEquals("my A", card.viewBy(owner));
        assertEquals("up A", card.viewBy(observer));

        card.relinquish();
        assertEquals("up A", card.viewBy(observer));

        Card faceDown = new Card("B");
        assertEquals("down", faceDown.viewBy(observer));
    }

    @Test
    public void removeMakesCardEmpty() {
        Card card = new Card("A");
        card.remove();

        assertTrue(card.isEmpty());
        assertEquals("", card.getSymbol());
        assertEquals("none", card.viewBy(new Player("any")));
        assertEquals("none", card.toString());
    }

    @Test
    public void replaceSymbolUpdatesSymbol() throws EmptyCardException {
        Card card = new Card("A");
        Player player = new Player("alice");
        Object notifier = new Object();

        player.turnOver(card, notifier);
        card.replaceSymbol("X");

        assertEquals("X", card.getSymbol());
        assertEquals("my X", card.viewBy(player));
    }

    @Test
    public void replaceSymbolNoOpWhenEmpty() {
        Card card = new Card("A");
        card.remove();

        card.replaceSymbol("X");
        assertEquals("", card.getSymbol());
    }

    @Test
    public void replaceSymbolRejectsNull() {
        Card card = new Card("A");
        assertThrows(IllegalArgumentException.class, () -> card.replaceSymbol(null));
    }

    @Test
    public void toStringReflectsState() throws EmptyCardException {
        Card card = new Card("A");
        Player player = new Player("alice");
        Object notifier = new Object();

        assertTrue(card.toString().startsWith("down"));

        player.turnOver(card, notifier);
        String upString = card.toString();
        assertTrue(upString.contains("up"));
        assertTrue(upString.contains("alice"));
        assertTrue(upString.contains("A"));

        card.relinquish();
        assertTrue(card.toString().startsWith("up"));

        card.remove();
        assertEquals("none", card.toString());
    }
}
