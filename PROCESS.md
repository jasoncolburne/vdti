# Building a complex, mission critical ecosystem with Anthropic's Claude

I started building something at the beginning of the year, to re-familiarize myself with Rust and
learn more about working with LLMs. I didn't start with design. This was my first mistake. The
reason this was such a mistake is that in this design, correctness is non-negotiable. Why? A single
assumption can underpin the security of the entire ecosystem.

As a seasoned developer, I can most often start implementation with only a rough idea of my goal in
my head, solving problems related to strategy and direction as I accrue information during
development. Claude, however, has a limited context window and cannot reason about the design as a
whole the same way I can. I was unnecessarily introducing a large burden of 'managing' Claude while
it worked.

What happened? I built a beautiful and performant decentralized ecosystem for establishing identity
and trust. It took about 5 months in my spare time, and it worked (I think) flawlessly. It was based
on existing work I became aware of a few years ago, but introduced new formalisms that allowed
interesting cryptographically-protective properties. It came complete with a slew of rust packages,
a kubernetes environment that could spin up for dev in simple or complex modes, a comprehensive
end-to-end test suite that exercised all functionality of the ecosystem, and much more.

The problem? A single design choice I made in haste was unsound. It worked, sure, but it introduced
an unacceptable attack vector that had no mitigation. In most cases, it's unlikely this type of
attack would succeed until several years after the data to be impacted had been consumed. But, not
wanting to constrain future users, I had to roll back that decision. This had a cascading effect
throughout my design, and introduced so much churn that I actually decided to do what I should have
done in the first place - design the entire ecosystem before beginning implementation, in a new
repository. The positive is that I had already roadmapped several other changes that became easier
to make in a new repository.

The rules for design are simple, now that I understand a bit more about how LLMs work:

0. Design is the leading edge, implementation follows.
   - In this class of system, a single wrong piece can sink the whole thing, so we pay the price of
     determining correctness up front.
1. Create a structured set of design documentation.
   - Why structured? This prevents the LLM from reading/grepping the entire design when it needs
     context. I used markdown with cross-referencing links throughout.
2. Define a concise set of project invariants.
   - This constrains the LLM when it reasons.
   - I often link this document from `CLAUDE.md` or `AGENTS.md` so the LLM always has it in context.
3. Use a durable, uncommitted work surface.
   - I create `.working/` directories in my projects and `.gitignore` them.
   - This prevents loss of context surrounding compaction. Create briefs, reviews, implementation,
     deviation and deferral logs, etc (have the LLM always create them) on the work surface and
     refer to them in prompts.
4. Use Claude's vernacular. You can use your own, but I find the models work best when you explain
   in terms they already use - it's like an established protocol, and allows you to catch the model
   reasoning in the wrong frame. - 'Locked' - decision made. - 'Drift' - usually related to
   documentation not being updated as required. - 'Fallout' - the changes to surrounding code
   required by the core change. - 'Invariant' - a system rule that cannot be broken - 'Gap' - a
   delta between design/correctness and implementation. - 'Surface' / 'canonical surface' - the
   single place the truth lives; everything else points at it. - 'Land' - to commit/merge a change
   onto the canonical surface. - 'Backport' - when a fix touches a pattern the symmetric side also
   has, apply it there in the same change. - 'Thin pointer' - a minimal reference to a durable doc,
   instead of duplicating its content. - 'Load-bearing' - a piece the design critically depends on;
   can't be simplified or removed without collapse. - 'Structural' (vs. 'incidental' /
   'current-state') - inherent to the design, not just how things happen to be right now. -
   'Smell' - a signal something is probably wrong before you can prove it. - 'Greenfield' - a fresh
   build with no migration path or legacy audience to accommodate. - 'Altitude' - the level of
   abstraction you're working at; "wrong altitude" = too in-the-weeds or too vague. - 'Telegraph' -
   make a doc or structure signal its purpose up front. - 'Punt' / 'Defer' - postpone deliberately
   (and log it, so it isn't lost). - 'Hygiene' - upkeep done proactively, before something forces
   it. - 'Triage' - sort findings/issues by what actually matters. - 'Fold' - incorporate changes
   into a written document - 'Fold these changes and we'll review'
5. Other useful terms:
   - Turn - A single message from you or the LLM
   - Round - The collection of turns between compactions
   - Session - A collection of rounds (multiple rounds across compactions)
6. Instruct the LLM to _attack_ the design, not affirm it. It should look for concrete examples
   where the design breaks down, to raise for resolution.
7. Instruct the LLM to read from source, not reason from context. This prevents staleness.
8. Tell the LLM to use 'property framing' when ensuring soundness. This changes statements like
   'attack and try to break X' to 'ensure soundness of X'. If you're using Fable to review,
   absolutely follow this advice or you'll be flagged.

# My design process (2026-07-09)

I now run a four agent (all Opus) topology:

1. Design (xhigh)
2. Implementation (high)
3. Cold review (max)
4. Warm review (max)

I compact design and warm review, and each keeps a resume.md file current in the working surface and
reads it after compaction to regain its own context.

Cold and warm review produce different, decorrelated results and it's incredibly useful to use both.
They don't share blind spots — warm is primed (checks fidelity, trusts the frame), cold is fresh
(attacks soundness).

## The process

1. I first design by working through the problems with the Design agent in conversation. Then, we
   _capture_ the ideas in the working surface.
2. I then perform as many dual-pass reviews (cold/warm) as required to iterate and resolve all open
   questions and soundness concerns.
3. After the reviewed _capture_, we _encode_ the captured ideas into a tracked part of the
   repository, `docs/canon`, in a machine readable format (the LLM reasons about the design using
   this source of truth).
4. Again, we iterate on dual-pass reviews until satisfied with the encoding.
5. Once the canon is _encoded_ and reviewed, we begin _encoding_ the design docs with these rules:
   a. Greenfield voice b. No jargon c. Human readable slug-style-references
6. Finally we go through another round of dual-pass reviews to nail down the design docs.

The product is a solid design, ready for implementation.
