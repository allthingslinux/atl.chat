A module providing a streaming statistics interface like
[mod_statistics] but based on the new [statistics API][doc:statistics]
introduced in Prosody 0.10.

# Usage

To use, enable the built-in statistics like so:

```lua
statistics = "internal"
```

Then, in `modules_enabled`, replace `"statistics"` with
`"statistics_statsman"` and the various `"statistics_<something>"`
with equivalent `"measure_<something>"`.


# Compatibility

  ------- --------------------
  trunk   Does not work [^1]
  0.11    Should work
  0.10    Should work
  ------- --------------------

[^1]: not after
    [5f15ab7c6ae5](https://hg.prosody.im/trunk/rev/5f15ab7c6ae5)
