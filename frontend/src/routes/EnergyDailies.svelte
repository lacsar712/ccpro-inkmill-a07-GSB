<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { EnergyDaily, EnergyDailySummary, Workshop } from '../lib/types';

  let rows: EnergyDaily[] = [];
  let workshops: Workshop[] = [];
  let summary: EnergyDailySummary | null = null;
  let error = '';
  let editingId: number | null = null;

  function todayLocal(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  function daysAgoLocal(n: number): string {
    const d = new Date();
    d.setDate(d.getDate() - n);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  let filter = {
    workshopId: '',
    startDate: daysAgoLocal(6),
    endDate: todayLocal(),
  };

  let form = {
    workshopId: '',
    workDate: todayLocal(),
    kwh: '',
    peakKw: '',
  };

  function workshopName(id: number): string {
    const w = workshops.find((x) => x.id === id);
    return w ? w.name : `#${id}`;
  }

  function fmt(v: number | null | undefined): string {
    return v == null || Number.isNaN(v) ? '—' : v.toFixed(2);
  }

  async function loadWorkshops() {
    workshops = await api<Workshop[]>('/workshops');
    if (!filter.workshopId && workshops[0]) filter.workshopId = String(workshops[0].id);
    if (!form.workshopId && workshops[0]) form.workshopId = String(workshops[0].id);
  }

  async function load() {
    error = '';
    try {
      const params = new URLSearchParams();
      if (filter.workshopId) params.set('workshopId', filter.workshopId);
      if (filter.startDate) params.set('startDate', filter.startDate);
      if (filter.endDate) params.set('endDate', filter.endDate);
      const qs = params.toString();
      [rows, summary] = await Promise.all([
        api<EnergyDaily[]>(`/energy-dailies?${qs}`),
        api<EnergyDailySummary>(`/energy-dailies/summary?${qs}`),
      ]);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  onMount(async () => {
    try {
      await loadWorkshops();
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  });

  function reset() {
    form = {
      workshopId: filter.workshopId || (workshops[0] ? String(workshops[0].id) : ''),
      workDate: todayLocal(),
      kwh: '',
      peakKw: '',
    };
    editingId = null;
  }

  function edit(row: EnergyDaily) {
    editingId = row.id;
    form = {
      workshopId: String(row.workshopId),
      workDate: row.workDate,
      kwh: String(row.kwh),
      peakKw: row.peakKw != null ? String(row.peakKw) : '',
    };
  }

  async function save() {
    error = '';
    const payload = {
      workshopId: Number(form.workshopId),
      workDate: form.workDate,
      kwh: Number(form.kwh),
      peakKw: form.peakKw === '' ? null : Number(form.peakKw),
    };
    try {
      if (editingId) {
        await api(`/energy-dailies/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
      } else {
        await api('/energy-dailies', { method: 'POST', body: JSON.stringify(payload) });
      }
      reset();
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '保存失败';
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该能耗日报？')) return;
    try {
      await api(`/energy-dailies/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '删除失败';
    }
  }
</script>

<header class="page-head">
  <h1>能耗日报</h1>
  <p>按车间登记每日用电量（kWh，非负）与可选峰值功率（kW），同车间同日唯一</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel">
  <h2>查询区间</h2>
  <div class="fields">
    <div class="field">
      <label>车间
        <select bind:value={filter.workshopId}>
          {#each workshops as w}
            <option value={String(w.id)}>{w.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>开始日期<input type="date" bind:value={filter.startDate} /></label></div>
    <div class="field"><label>结束日期<input type="date" bind:value={filter.endDate} /></label></div>
    <div class="field query">
      <button class="btn-primary" on:click={load}>查询</button>
    </div>
  </div>
  {#if summary}
    <div class="totals">
      <div class="stat">
        <div class="k">区间合计用电量</div>
        <div class="v accent">{fmt(summary.totalKwh)} <span>kWh</span></div>
      </div>
      <div class="stat">
        <div class="k">日报天数</div>
        <div class="v">{summary.dayCount} <span>天</span></div>
      </div>
      <div class="stat">
        <div class="k">区间最大峰值</div>
        <div class="v">{fmt(summary.maxPeakKw)} <span>kW</span></div>
      </div>
    </div>
  {/if}
</section>

<section class="panel">
  <h2>{editingId ? '编辑日报' : '新增日报'}</h2>
  <div class="fields">
    <div class="field">
      <label>车间
        <select bind:value={form.workshopId}>
          {#each workshops as w}
            <option value={String(w.id)}>{w.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field"><label>日期<input type="date" bind:value={form.workDate} /></label></div>
    <div class="field"><label>用电量 kWh<input type="number" min="0" step="0.01" bind:value={form.kwh} /></label></div>
    <div class="field"><label>峰值 kW（可空）<input type="number" min="0" step="0.01" bind:value={form.peakKw} /></label></div>
  </div>
  <div class="actions">
    <button class="btn-primary" on:click={save}>{editingId ? '保存' : '创建'}</button>
    {#if editingId}
      <button class="btn-ghost" on:click={reset}>取消</button>
    {/if}
  </div>
</section>

<section class="panel">
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>车间</th>
        <th>日期</th>
        <th>用电量 kWh</th>
        <th>峰值 kW</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{workshopName(row.workshopId)}</td>
          <td>{row.workDate}</td>
          <td>{fmt(row.kwh)}</td>
          <td>{fmt(row.peakKw)}</td>
          <td class="ops">
            <button class="link-btn" on:click={() => edit(row)}>编辑</button>
            <button class="link-btn danger" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {:else}
        <tr><td colspan="6">该区间暂无能耗日报</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .totals {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
    margin-top: 1.1rem;
  }

  .stat {
    padding: 1rem 1.1rem;
    background: rgba(10, 10, 10, 0.6);
    border: 1px solid var(--line);
    border-top: 3px solid var(--ink-700);
  }

  .stat:first-child {
    border-top-color: var(--vermillion-700);
  }

  .k {
    color: var(--steel);
    font-size: 0.85rem;
  }

  .v {
    margin-top: 0.45rem;
    font-family: var(--font-display);
    font-size: 1.9rem;
    letter-spacing: 0.04em;
  }

  .v span {
    font-size: 0.85rem;
    color: var(--steel);
    letter-spacing: 0;
  }

  .accent {
    color: var(--vermillion-400);
  }

  .query {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
  }

  @media (max-width: 900px) {
    .totals {
      grid-template-columns: 1fr;
    }
  }
</style>
