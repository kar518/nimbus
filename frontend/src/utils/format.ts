export function date(value: string | null, options?: Intl.DateTimeFormatOptions): string {
  if (!value) return "—";
  return new Date(
    value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : value + "Z"
  ).toLocaleString(
    undefined,
    options ?? { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }
  );
}
export function duration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const parse = (v: string) =>
    new Date(v.endsWith("Z") || /[+-]\d\d:\d\d$/.test(v) ? v : v + "Z").getTime();
  const seconds = Math.max(0, Math.round(((end ? parse(end) : Date.now()) - parse(start)) / 1000));
  return seconds < 60
    ? `${seconds}s`
    : seconds < 3600
      ? `${Math.floor(seconds / 60)}m ${seconds % 60}s`
      : `${Math.floor(seconds / 3600)}h ${Math.floor(seconds / 60) % 60}m`;
}
export function memory(mb: number): string {
  return mb >= 1024 ? `${(mb / 1024).toFixed(mb % 1024 ? 1 : 0)} GB` : `${mb} MB`;
}
