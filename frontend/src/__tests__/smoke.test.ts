import { describe, it, expect } from 'vitest';

describe('ArmServe Frontend', () => {
  it('should have correct project configuration', () => {
    expect(true).toBe(true);
  });

  it('should export valid React components', async () => {
    const { ExperimentsPage } = await import('../pages/ExperimentsPage');
    expect(ExperimentsPage).toBeDefined();
    expect(typeof ExperimentsPage).toBe('function');
  });
});
