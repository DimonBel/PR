/* Copyright (c) 2017-2020 MIT 6.031 course staff, all rights reserved.
 * Redistribution of original or derived work requires permission of course staff.
 */
package memory;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

public class PlayerTest {
    @Test
    public void testAssertionsEnabled() {
        assertThrows(AssertionError.class, () -> {
            assert false;
        }, "make sure assertions are enabled with VM argument '-ea'");
    }

    @Test
    public void playerStoresNameAndInitialState() {
        Player player = new Player("smith");
        assertEquals("smith", player.getName());
        assertEquals(0, player.getScore());
        assertEquals(0, player.size());
    }

    @Test
    public void turnOverSetsCardFaceUpAndControlled() throws EmptyCardException {
        Player player = new Player("alice");
        Card card = new Card("A");
        Object notifier = new Object();

        player.turnOver(card, notifier);

        assertTrue(card.isUp());
        assertTrue(card.isControlled());
        assertEquals(player, card.getOwner());
        assertEquals(1, player.size());
    }

    @Test
    public void nonMatchingCardsAreRelinquished() throws EmptyCardException {
        Player player = new Player("alice");
        Card first = new Card("A");
        Card second = new Card("B");
        Object notifier = new Object();

        player.turnOver(first, notifier);
        player.turnOver(second, notifier);

        assertEquals(2, player.size());
        assertFalse(first.isControlled());
        assertFalse(second.isControlled());
        assertTrue(first.isUp());
        assertTrue(second.isUp());

        Card third = new Card("C");
        player.turnOver(third, notifier);
        assertEquals(1, player.size());
        assertTrue(third.isControlled());
    }

    @Test
    public void matchingCardsIncreaseScoreOnNextTurn() throws EmptyCardException {
        Player player = new Player("alice");
        Card first = new Card("A");
        Card second = new Card("A");
        Card third = new Card("B");
        Object notifier = new Object();

        player.turnOver(first, notifier);
        player.turnOver(second, notifier);
        assertEquals(2, player.size());
        assertEquals(0, player.getScore());
        assertTrue(first.isControlled());
        assertTrue(second.isControlled());

        player.turnOver(third, notifier);

        assertEquals(1, player.getScore());
        assertTrue(first.isEmpty());
        assertTrue(second.isEmpty());
        assertEquals(1, player.size());
        assertTrue(third.isControlled());
    }

    @Test
    public void equalsAndHashCodeUseName() {
        Player alice1 = new Player("alice");
        Player alice2 = new Player("alice");
        Player bob = new Player("bob");

        assertEquals(alice1, alice2);
        assertEquals(alice1.hashCode(), alice2.hashCode());
        assertNotEquals(alice1, bob);
    }
}
