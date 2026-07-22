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
   reasoning in the wrong frame.
   - 'Locked' - decision made.
   - 'Drift' - usually related to documentation not being updated as required.
   - 'Fallout' - the changes to surrounding code required by the core change.
   - 'Invariant' - a system rule that cannot be broken
   - 'Gap' - a delta between design/correctness and implementation.
   - 'Surface' / 'canonical surface' - the single place the truth lives; everything else points at
     it.
   - 'Land' - to commit/merge a change onto the canonical surface.
   - 'Backport' - when a fix touches a pattern the symmetric side also has, apply it there in the
     same change.
   - 'Thin pointer' - a minimal reference to a durable doc, instead of duplicating its content.
   - 'Load-bearing' - a piece the design critically depends on; can't be simplified or removed
     without collapse.
   - 'Structural' (vs. 'incidental' / 'current-state') - inherent to the design, not just how things
     happen to be right now.
   - 'Smell' - a signal something is probably wrong before you can prove it.
   - 'Greenfield' - a fresh build with no migration path or legacy audience to accommodate.
   - 'Altitude' - the level of abstraction you're working at; "wrong altitude" = too in-the-weeds or
     too vague.
   - 'Telegraph' - make a doc or structure signal its purpose up front.
   - 'Punt' / 'Defer' - postpone deliberately (and log it, so it isn't lost).
   - 'Hygiene' - upkeep done proactively, before something forces it.
   - 'Triage' - sort findings/issues by what actually matters.
   - 'Fold' - incorporate changes into a written document - 'Fold these changes and we'll review'
5. Other useful terms:
   - Turn - A single message from you or the LLM
   - Round - A review cycle
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

_(Stages 3–6 have run their course for the core design: the canon was fully propagated into the
design docs and the encoded canon files were then removed — their decision history is preserved at
the `canon-final` git tag. `docs/canon/` retains only not-yet-encoded notes.)_

## Details

I made most positive additions by teasing apart conflated axes. An example - the {content, lineage}
fields on a SEL Icp. During design, solving routine data modelling problems with these primitives, I
realized I needed lineage if we wanted to be able to re-issue data under the same topic. I landed on
the rule that lineage should be omitted to make the chain monotone, but didn't realize that in my
reasoning I was conflating content with lineage, and trying to make up strange rules based on kind
and tier that composed for the correct result, when the solution was really separating the two
fields and making them optional on the SEL Icp. The `content` field, when present, is `true` and
indicates that a T1 v1 should follow. If omitted, a T2 v1 must follow. This was a massive
simplificiation and allowed the completion of the SEL primitive.

The most obvious example of pulling apart conflated axes is _device_ and _identity_. By separating
the two, at the cost of a bit more complexity in the data, we are able to more effectively manage
application and user security concerns.

I made most positive subtractions (and there were many) by first conceiving of and designing a
feature that I believed to be sound, and having myself and Claude discuss it with the specific
framing that it should attempt to _break_, not _affirm_ my claims. If it was unable, we'd continue
or dig deeper (guided mostly by my instinct).

## The design capabilities of Claude code

I tried Fable for a brief period, and was flagged about 25-50% of the time. It did make a couple
good finds, but I was using it to review in both a cold and warm context, so I'm not sure how it
performs outside that use case. It wasn't that different to be honest. It babbles less while
'thinking', I did notice that. Not sure if that's to conserve context, prevent previous bias, or
what. I kind of prefer Opus.

Claude is more than capable of verifying design work, but it takes several iterations of review to
get there. It's not good at seeing beyond the next chess move, but it's very good at understanding
the present limitations and benefits of a design. Without full context, as always, mis-reasoning is
a risk.

What it's _not_ capable of doing (at least Opus 4.8), is having security and design insights that
rival my own. It's an impressive tool, but it's very much a tool at present. I use it as a sounding
board for the most part, though it sometimes makes good simplifications and does add occasional
value to the process. On the whole however, against a human designer/colleague, we'd get from A to B
much faster as humans. That said, those humans would cost far more than an Anthropic subscription.

That said, after designing the primitives Claude did compose them very easily, understanding
quickly.

On the whole - for a critical, design-heavy project, Claude is an amazing resource for a small team
that simply needs extra high-quality review capacity.

## The implementation capabilities of Claude code

I think we are all aware by now that with a good specification, Claude's implementation skills are
quite impressive. The reason I have created the process above, is that without solid foundational
design, Claude will make decisions unless explicitly told not to.

The decisions that Claude makes can be great, don't get me wrong; but often it isn't framing the
problem the same way I am. It's missing valuable context that drives a decision in one direction or
another.

Another problem you can run into with LLMs is hygeine. I am very strict to ensure that we re-use and
reference where possible, use consistent naming and convention, and generally keep things tidy. If
you don't make standing memories or rules for the LLM to reason with, it may implement naively -
duplicating concepts or code, making things generally hard to work with (for you or even _it_ in the
future).

# Conclusion

Claude is an asset to the lone wolf security designer. I use it to:

- challenge and validate the soundness of my designs
- capture design ideas
- encode canonical design reference (machine readable)
- encode design documentation (human readable)
- implement design
