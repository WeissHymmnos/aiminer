type Props = {
  value: unknown;
};

export function JsonView({ value }: Props) {
  return <pre className="code-block">{JSON.stringify(value, null, 2)}</pre>;
}
