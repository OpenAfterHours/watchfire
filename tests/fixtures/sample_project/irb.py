"""IRB approach — uses a mix of CRR articles and a PRA supervisory statement."""

import watchfire


@watchfire.cites("CRR Art. 153(1)(a)")
def corporate_rw(pd, lgd):
    return pd * lgd


@watchfire.cites("CRR Art. 154(1)")
def retail_rw(pd, lgd):
    return pd * lgd


@watchfire.cites("SS1/23, paragraph 2.5")
def model_validation():
    return True


@watchfire.cites("CRR Art. 4(1)(75)")
def is_corporate(entity):
    return True
