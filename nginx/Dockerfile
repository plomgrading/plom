# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

FROM nginx:1.25.1-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY default.conf /etc/nginx/conf.d
COPY plom-selfsigned.crt plom-selfsigned.key /etc/ssl/private/
