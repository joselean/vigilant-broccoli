import { config, isHetznerConfigured } from "./config";

export interface CreateServerParams {
  name: string;
  serverType: string;
  location: string;
  image: string;
}

export interface CreateServerResult {
  hetznerServerId: string;
  ipv4: string | null;
  ipv6: string | null;
  rootPassword: string | null;
}

const HETZNER_API_URL = "https://api.hetzner.cloud/v1";

async function realCreateServer(params: CreateServerParams): Promise<CreateServerResult> {
  const body: Record<string, unknown> = {
    name: params.name,
    server_type: params.serverType,
    location: params.location,
    image: params.image,
  };

  if (config.hetznerSshKeyId) {
    body.ssh_keys = [Number(config.hetznerSshKeyId)];
  }

  const res = await fetch(`${HETZNER_API_URL}/servers`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.hetznerApiToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Hetzner API error (${res.status}): ${text}`);
  }

  const data = (await res.json()) as {
    server: {
      id: number;
      public_net: { ipv4?: { ip: string }; ipv6?: { ip: string } };
    };
    root_password?: string;
  };

  return {
    hetznerServerId: String(data.server.id),
    ipv4: data.server.public_net.ipv4?.ip ?? null,
    ipv6: data.server.public_net.ipv6?.ip ?? null,
    rootPassword: data.root_password ?? null,
  };
}

async function demoCreateServer(params: CreateServerParams): Promise<CreateServerResult> {
  // Used while HETZNER_API_TOKEN is not configured yet, so the full order ->
  // provisioning -> notification flow can be tested end to end.
  await new Promise((resolve) => setTimeout(resolve, 1500));
  const octet = Math.floor(Math.random() * 254) + 1;
  return {
    hetznerServerId: `demo-${Date.now()}`,
    ipv4: `203.0.113.${octet}`,
    ipv6: null,
    rootPassword: `Demo-${Math.random().toString(36).slice(2, 10)}!`,
  };
}

export const hetznerClient = {
  createServer(params: CreateServerParams): Promise<CreateServerResult> {
    return isHetznerConfigured() ? realCreateServer(params) : demoCreateServer(params);
  },
};
