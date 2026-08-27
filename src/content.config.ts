import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

/**
 * The course, as data.
 *
 * A unit is a chunk of material, not a length of time, and it is split into
 * sessions of one sitting each. Every session has a matching deck; a session
 * is not finished until its deck exists, which is why `deck` is required and
 * the decks are a collection in their own right rather than a loose file.
 */

const units = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/units" }),
  schema: z.object({
    number: z.number().int().positive(),
    title: z.string(),
    /** One line under the title: what this unit is for. */
    standfirst: z.string(),
    /** Move on when these are true, not when the material has been covered. */
    canDos: z.array(z.string()).min(1),
    /**
     * The can-do to hold the line on, if one of them carries the unit. Written
     * per unit because it is about that unit's material — a note in the
     * template would be Unit 1's opinion printed on Unit 14.
     */
    insist: z.string().optional(),
    /**
     * What to do when the unit goes badly. Inline HTML, like the leads: the
     * template decides where it goes so every unit's page reads the same way.
     */
    contingency: z.array(z.string()).optional(),
  }),
});

const sessions = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/sessions" }),
  schema: z.object({
    unit: z.number().int().positive(),
    number: z.number().int().positive(),
    title: z.string(),
    standfirst: z.string(),
    /** How it reads on the unit's contents list. */
    summary: z.string(),
    /** One sitting. Longer than 40 on paper means it should be two sessions. */
    minutes: z.number().int().min(15).max(45),
    /** What the deck page says about itself. */
    deckStandfirst: z.string(),
  }),
});

const decks = defineCollection({
  /**
   * One file per session, named to match the session it belongs to — 01-2.json
   * is the deck for src/content/sessions/01-2.mdx. The id comes from the
   * filename, so a new deck is a new file and nothing central has to be edited.
   */
  loader: glob({ pattern: "**/*.json", base: "./src/data/decks" }),
  schema: z.object({
    unit: z.number().int().positive(),
    session: z.number().int().positive(),
    /**
     * Notes shown above the deck, collapsed. Every deck says what it cannot
     * do: anything resting on hearing or producing a sound cannot be tested by
     * a card, and the teacher needs to know which decks need them in the room.
     */
    notes: z.array(z.object({ lead: z.string(), body: z.string() })),
    cards: z.array(
      z.object({
        /** Deck name. Decks run in teaching order, most fundamental first. */
        d: z.string(),
        /** A rule card is a question and is never reversed. */
        t: z.enum(["word", "rule"]),
        f: z.string(),
        s: z.string().optional(),
        m: z.string(),
      }),
    ).min(1),
  }),
});

const reference = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/reference" }),
  schema: z.object({
    title: z.string(),
    standfirst: z.string(),
    /** Position on the contents page. */
    order: z.number().int(),
    /** The one-word label on its card. */
    kind: z.string(),
    blurb: z.string(),
  }),
});

export const collections = { units, sessions, decks, reference };
