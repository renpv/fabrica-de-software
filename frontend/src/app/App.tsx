import { MantineProvider } from "@mantine/core";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { criarQueryClient } from "../api/queryClient";
import { tema } from "../tema/tema";
import { RotasApp } from "./rotas";

const queryClient = criarQueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider theme={tema}>
        <BrowserRouter>
          <RotasApp />
        </BrowserRouter>
      </MantineProvider>
    </QueryClientProvider>
  );
}
