# bbs — the public message board

`bbs` is a forum: boards, threads, replies, edits, moderation — with every post attributed to a real
identity, provably, which is the property that makes it worth building on this substrate at all. It
is the composition case for **shared documents alone**, and it absorbs the catalogue's
same-composition variants: the **wiki / knowledge base** and **code hosting / version control** are
the same construct with the emphasis moved from the comment tree to the version DAG (below).

## The composition

A board is a **shared document**
([`../features/shared-documents.md`](../features/shared-documents.md)); the forum's parts map onto
the feature's parts with nothing invented:

- **The board is the document.** Its constitution derives the board's identity; its version DAG
  carries the board's slowly-evolving front matter — the charter, the rules, the sticky list —
  authored by the operators. A public board omits `readers`; a members-only board gates reads by the
  same membership machinery everything else here uses
  ([`../features/shared-documents.md` §Sharing, custody, and privacy](../features/shared-documents.md#sharing-custody-and-privacy)).
- **Posts are comments.** The feature's comment kind is the post, exactly as specified: a
  direct-anchored SAD, provably authored by its poster, `target` naming the charter version it posts
  under, `parent` threading replies into a tree, `supersedes` carrying self-edits (the edit is the
  link — no mutable post, no edit flag), and the `locator` left to the application — here, the
  thread discriminator
  ([`../features/shared-documents.md` §Comments](../features/shared-documents.md#comments)).
- **Posting rights are the comment membership.** Joining the board is a grant into the board's
  comment set; the operators are its editors. Moderation is the rescission machinery working as
  designed: rescinding a poster closes their bracket at a bound of the operator's choosing —
  grandfather everything and stop only future posts, or cut back to last-good — and a banned
  poster's later posts fail the honored window on their own append-only chain, backdate closed both
  ways
  ([`../features/shared-documents.md` §The honored predicate](../features/shared-documents.md#the-honored-predicate)).
- **Locking a thread or the board** is presentation plus membership: a locked board is the feature's
  freeze (bound every bracket, terminate the grant chains); a locked thread is the application
  declining to render replies past a marker — structure the app arbitrates, as the feature
  prescribes for everything the data does not itself order.

## Scenarios

- **Post and reply.** A member authors a comment SAD, anchors it on their own IEL, and hands it to
  the board's nodes. Any reader verifies the post's authorship (the anchor), its standing (the
  poster's bracket was open at the anchor position), and its place in the thread (the parent chain)
  — from the data, from any node.
- **Edit your post.** A `supersedes` comment by the same author; the tree renders the tip. The
  history stays — an edit on this board is honest by construction.
- **Ban a spammer.** Rescind the poster's comment grant at the detection tip: their existing posts
  stay (grandfathered, as forums expect), their next post is structurally un-honored everywhere —
  not deleted by one server, refused by every verifier.
- **Fork the board.** Operators gone rogue is the feature's creator-compromise posture: the
  community reincepts a fresh constitution seeded from the front matter it likes, and the old board
  stays verifiable. Nothing structural picks the successor — legitimacy is social, stated as such
  ([`../features/shared-documents.md` §Trust posture](../features/shared-documents.md#trust-posture)).

## The wiki and the code host, absorbed

Move the weight from the comment tree to the **version DAG** and the same construct is the other two
catalogue entries:

- **Wiki**: a document per page; concurrent edits branch and merge as the multi-parent DAG
  prescribes; page history is the DAG itself, every version attributed and anchored; the
  edit/comment/read triad is the wiki's protection levels
  ([`../features/shared-documents.md` §Versions](../features/shared-documents.md#versions--the-authored-dag)).
- **Code hosting**: the version DAG **is** a signed commit DAG — branch, merge, attribution by the
  branch root, tags as the feature's canonical-choice tags (an edit like any other, conflicts
  arbitrated by the application). What a central forge holds as its database — who may push, who
  authored what, what history is — is here carried by the data and checkable by any clone.

The board is the chosen carrier because it exercises the comment machinery the other two barely
touch; all three ride identically on the version-and-membership core.

## What this validates

- **A whole social application with no server-side authority.** Who may post, who posted what, what
  was edited, who was banned and from when — every question a forum's moderators and users ask is
  answered by the data, identically at every node. The "no trusted backend" claim carried to the
  most operator-shaped application in the set.
- **Moderation semantics are structural, not janitorial.** A ban is a rescission with a chosen bound
  — an authorization fact every verifier enforces — rather than a row deleted on one host.
- **The presented-not-picked posture holds up in practice.** Thread locking, sticky order, which
  edit of a contested charter renders — the feature hands structure, the application arbitrates, and
  nothing in the forum needed a structural decision the data could not carry.

## Limits

- **Immutability cuts both ways.** A post, once landed and held by others, cannot be unpublished —
  moderation un-honors and stops rendering; it does not recall bytes. A board that must purge
  content (legal takedown) does so at its own stores — availability expiry and store-side deletion —
  while copies others hold remain their copies. This is the substrate's honesty, not a gap the
  application papers over.
- **Attributed posting is the design point, not a mode.** A post is a direct-anchored SAD; there is
  no anonymous posting in this composition — an anonymous drop-box is a different custody shape with
  none of the thread-authorization machinery, and a board of unattributed posts would forfeit
  exactly the property this application demonstrates. Pseudonymity is available the honest way: an
  identity is a prefix, and linking it to a person is a credential question this composition
  deliberately does not compose.
- **Volume-timing is visible.** A private board's membership graph stays closed, but grant,
  rescission, and post-anchor volume-timing is the feature's stated mesh residual
  ([`../features/shared-documents.md` §Boundary / residuals](../features/shared-documents.md#boundary--residuals)).
