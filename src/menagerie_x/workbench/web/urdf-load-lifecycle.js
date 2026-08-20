/** Tracks the one render generation permitted to attach asynchronous meshes. */
export function createUrdfLoadGate() {
  let generation = 0;
  return {
    begin() {
      const token = ++generation;
      return { token, current: () => token === generation };
    },
    invalidate() { generation += 1; },
  };
}
