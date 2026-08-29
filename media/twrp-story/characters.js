/* Original, self-contained SVG actors for From Black Screen to TWRP.
 *
 * render(kind, prefix) gives every internal SVG ID a caller-owned prefix.
 * .char-body contains the complete actor; .char-head contains its face.
 * Mouths and eyes use their own fill boxes for safe scaleY animation.
 * Arms expose SVG-space shoulder pivots in data-pivot-x / data-pivot-y.
 * The open mouth is visible initially; the closed smile starts at opacity 0.
 * No timers or animation run here: the composition owns all seekable motion.
 */
(function (global) {
  "use strict";

  const ink = "#20343C";
  const paper = "#F6F0E5";
  const coral = "#EC7955";
  const teal = "#187568";
  const amber = "#EAB850";
  const faceRig = 'style="transform-box:fill-box;transform-origin:center"';

  function nezha(prefix) {
    return `
      <g class="char-body" style="transform-box:view-box;transform-origin:210px 452px">
        <g class="char-legs" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M160 351 L151 410 Q165 421 179 409 L182 354" fill="${coral}"/>
          <path d="M240 355 L249 409 Q263 418 276 407 L268 351" fill="${coral}"/>
          <path d="M147 401 L178 402 L180 420 L144 420 Z" fill="${paper}"/>
          <path d="M249 402 L277 402 L279 421 L248 421 Z" fill="${paper}"/>
          <path d="M152 409 L174 410 M254 411 L274 410" stroke="${teal}" stroke-width="4"/>
          <path d="M144 415 Q129 411 116 424 L101 435 Q96 440 103 450 L181 450 Q188 443 183 425 L178 416 Z" fill="${paper}"/>
          <path d="M250 416 Q267 414 279 420 L301 433 Q309 438 305 450 L244 450 Q236 444 241 428 Z" fill="${paper}"/>
          <path d="M102 441 L183 441 M244 442 L305 442" fill="none" stroke-width="5"/>
          <path d="M133 424 L145 432 M145 421 L156 429 M263 423 L257 431 M275 427 L268 434" fill="none" stroke-width="4"/>
        </g>

        <g class="char-arm-left" data-pivot-x="112" data-pivot-y="247" style="transform-box:view-box;transform-origin:112px 247px" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M110 247 Q79 259 75 292 L69 312" fill="none" stroke-width="20"/>
          <path d="M110 247 Q79 259 75 292 L69 312" fill="none" stroke="${coral}" stroke-width="11"/>
          <path d="M60 303 Q70 299 81 308 L87 324 Q91 333 82 338 L81 351 Q78 361 69 357 L60 352 Q48 347 49 333 L51 320 Q44 312 48 306 Q52 299 60 303 Z" fill="${paper}" stroke-width="5.5"/>
          <path d="M62 330 L60 341 M72 329 L70 345 M54 318 Q62 314 64 323" fill="none" stroke-width="3.5"/>
        </g>

        <g class="char-arm-right" data-pivot-x="309" data-pivot-y="243" style="transform-box:view-box;transform-origin:309px 243px" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M309 243 Q331 258 344 236 L354 216" fill="none" stroke-width="20"/>
          <path d="M309 243 Q331 258 344 236 L354 216" fill="none" stroke="${coral}" stroke-width="11"/>
          <path d="M345 220 Q334 211 338 200 L345 185 Q348 180 354 184 L362 159 Q364 153 370 155 Q377 157 374 164 L368 187 L379 177 Q385 173 389 178 Q393 182 388 188 L377 200 Q387 194 391 201 Q394 207 386 213 L375 223 Q362 233 345 220 Z" fill="${paper}" stroke-width="5.5"/>
          <path d="M350 195 Q360 195 364 205 M369 209 L380 204" fill="none" stroke-width="3.5"/>
        </g>

        <g class="char-head" style="transform-box:view-box;transform-origin:211px 309px" stroke="${ink}" stroke-linecap="round" stroke-linejoin="round">
          <path d="M108 133 L100 133 Q96 133 96 138 L96 159 Q96 164 103 164 L108 164" fill="#CF6245" stroke-width="5"/>
          <path d="M311 126 L321 126 Q327 126 327 133 L327 167 Q327 174 319 174 L312 174" fill="#CF6245" stroke-width="5"/>
          <rect x="106" y="48" width="212" height="327" rx="43" fill="${coral}" stroke-width="8"/>
          <path d="M299 67 Q309 78 309 103 L309 328 Q309 362 278 365 L157 365 Q133 365 121 346 Q137 355 156 355 L271 355 Q293 355 293 329 L293 96 Q293 79 287 68" fill="#CF6245" stroke="none"/>
          <path d="M121 119 L121 93 Q121 67 146 64 L169 64" fill="none" stroke="#F6B497" stroke-width="6"/>
          <rect x="126" y="84" width="172" height="240" rx="28" fill="${paper}" stroke-width="5.5"/>
          <path d="M131 282 Q153 301 183 300 L266 300 Q284 300 293 286 L293 296 Q293 319 272 319 L151 319 Q131 317 131 296 Z" fill="#E9E0D0" stroke="none"/>
          <path d="M185 65 L234 65" stroke-width="8"/>
          <circle cx="246" cy="65" r="4" fill="${ink}" stroke="none"/>

          <g class="char-brows" fill="none" stroke-width="6">
            <path d="M151 139 Q166 129 183 134"/>
            <path d="M235 132 Q251 125 268 135"/>
          </g>
          <g class="char-eyes" ${faceRig}>
            <g class="char-eye-left" ${faceRig}>
              <ellipse cx="172" cy="174" rx="25" ry="31" fill="#FFFDF7" stroke-width="4.5"/>
              <ellipse cx="179" cy="177" rx="12" ry="18" fill="${ink}" stroke="none"/>
              <circle cx="182" cy="170" r="4.5" fill="#FFFDF7" stroke="none"/>
            </g>
            <g class="char-eye-right" ${faceRig}>
              <ellipse cx="253" cy="170" rx="24" ry="30" fill="#FFFDF7" stroke-width="4.5"/>
              <ellipse cx="259" cy="174" rx="11.5" ry="18" fill="${ink}" stroke="none"/>
              <circle cx="262" cy="167" r="4.5" fill="#FFFDF7" stroke="none"/>
            </g>
          </g>
          <ellipse cx="150" cy="214" rx="12" ry="7" fill="#F1B7A1" stroke="none"/>
          <ellipse cx="274" cy="210" rx="12" ry="7" fill="#F1B7A1" stroke="none"/>
          <path d="M211 192 L215 205 L208 206" fill="none" stroke-width="4"/>
          <g class="char-mouth-open" ${faceRig}>
            <path d="M182 222 Q210 215 239 219 Q236 249 213 251 Q188 252 182 222 Z" fill="${ink}" stroke-width="4"/>
            <path d="M190 223 Q210 220 231 222 L228 229 Q210 232 193 229 Z" fill="#FFFDF7" stroke="none"/>
            <path d="M201 245 Q212 234 226 241 Q220 248 213 248 Q206 248 201 245 Z" fill="${coral}" stroke="none"/>
          </g>
          <g class="char-mouth-closed" ${faceRig} opacity="0">
            <path d="M188 228 Q213 247 237 224" fill="none" stroke-width="5"/>
            <path d="M186 223 L185 229 M238 219 L241 225" fill="none" stroke-width="3.5"/>
          </g>
          <path d="M190 343 L231 343" fill="none" stroke-width="5"/>
          <circle cx="150" cy="342" r="4" fill="#F6B497" stroke="none"/>
          <circle cx="272" cy="342" r="4" fill="#CF6245" stroke="none"/>
        </g>
      </g>`;
  }

  function patch(prefix) {
    return `
      <g class="char-body" style="transform-box:view-box;transform-origin:210px 452px">
        <g class="char-legs" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M167 368 L161 413 L181 423 L192 372" fill="${teal}"/>
          <path d="M230 371 L238 416 L259 412 L258 366" fill="${teal}"/>
          <path d="M163 389 L185 392 M236 391 L257 387" stroke="#94B7A8" stroke-width="5"/>
          <path d="M157 408 Q173 409 184 416 L185 441 Q184 450 176 450 L112 450 Q103 440 113 430 L140 413 Q149 406 157 408 Z" fill="${coral}"/>
          <path d="M238 416 Q248 407 262 408 L288 425 Q300 433 300 444 Q301 450 294 450 L237 450 Q230 447 232 435 Z" fill="${coral}"/>
          <path d="M109 440 L182 440 L182 449 L113 449 Z M234 440 L298 440 L296 449 L237 449 Z" fill="${paper}" stroke="none"/>
          <path d="M110 440 L183 440 M234 440 L298 440" fill="none" stroke-width="4"/>
          <path d="M147 418 L158 426 M137 424 L148 432 M255 421 L247 429 M266 427 L258 434" fill="none" stroke="${paper}" stroke-width="4"/>
        </g>

        <g class="char-arm-left" data-pivot-x="143" data-pivot-y="283" style="transform-box:view-box;transform-origin:143px 283px" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M143 282 Q103 281 95 317 L89 333" fill="none" stroke-width="26"/>
          <path d="M143 282 Q103 281 95 317 L89 333" fill="none" stroke="${teal}" stroke-width="16"/>
          <circle cx="99" cy="305" r="12" fill="#94B7A8" stroke-width="5"/>
          <path d="M80 325 L98 331 L96 342 L77 337 Z" fill="${amber}" stroke-width="4.5"/>
          <path d="M78 337 Q62 337 64 352 L68 368 Q70 377 79 375 L92 370 Q101 365 98 356 L94 347 Q89 333 78 337 Z" fill="${paper}" stroke-width="5.5"/>
          <path d="M77 354 L81 365 M85 351 L90 360" fill="none" stroke-width="3.5"/>
        </g>

        <g class="char-arm-right" data-pivot-x="279" data-pivot-y="282" style="transform-box:view-box;transform-origin:279px 282px" stroke="${ink}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M279 282 Q315 306 327 276 L340 254" fill="none" stroke-width="26"/>
          <path d="M279 282 Q315 306 327 276 L340 254" fill="none" stroke="${teal}" stroke-width="16"/>
          <circle cx="315" cy="289" r="12" fill="#94B7A8" stroke-width="5"/>
          <path d="M328 255 L343 264 L350 251 L335 243 Z" fill="${amber}" stroke-width="4.5"/>
          <path d="M336 245 Q326 237 330 228 L335 216 Q338 212 343 214 L348 194 Q350 188 356 190 Q362 192 360 198 L356 219 L369 209 Q375 205 379 211 Q382 216 377 221 L367 231 Q378 226 381 233 Q383 238 376 243 L364 252 Q350 261 336 245 Z" fill="${paper}" stroke-width="5.5"/>
          <path d="M339 226 Q349 227 352 235 M361 241 L371 237" fill="none" stroke-width="3.5"/>
        </g>

        <g class="char-torso" stroke="${ink}" stroke-linecap="round" stroke-linejoin="round">
          <path d="M149 261 Q210 244 272 260 L286 352 Q287 373 267 379 L156 379 Q135 373 136 353 Z" fill="${teal}" stroke-width="7"/>
          <path d="M269 267 L279 350 Q281 369 262 372 L164 372 Q148 370 146 358 L257 358 Q269 357 267 343 L257 269" fill="#125B52" stroke="none"/>
          <rect x="187" y="242" width="49" height="30" rx="10" fill="#94B7A8" stroke-width="6"/>
          <path d="M191 253 L232 253" fill="none" stroke-width="4"/>
          <path d="M164 268 L180 270 L178 297 L162 296 Z M243 270 L259 268 L261 297 L245 297 Z" fill="${amber}" stroke-width="4.5"/>
          <path d="M163 287 Q210 278 258 287 L270 368 Q271 380 258 384 L163 384 Q151 381 153 369 Z" fill="${paper}" stroke-width="5.5"/>
          <path d="M258 294 L266 368 Q267 379 255 379 L164 379 Q157 377 158 370 L249 370 Q256 369 255 361 L247 294" fill="#E9E0D0" stroke="none"/>
          <circle cx="171" cy="290" r="4.5" fill="${ink}" stroke="none"/>
          <circle cx="251" cy="290" r="4.5" fill="${ink}" stroke="none"/>
          <g class="char-tools">
            <path d="M223 343 L216 310 Q205 307 207 297 L213 301 L217 297 L214 289 Q228 290 226 304 L234 340 Z" fill="${amber}" stroke-width="4"/>
            <path d="M192 341 L197 310 L204 311 L200 343 Z" fill="${coral}" stroke-width="3.5"/>
            <path d="M198 310 L200 299" fill="none" stroke-width="4"/>
          </g>
          <path d="M177 330 Q211 334 246 330 L242 355 Q241 363 231 364 L190 364 Q181 362 181 354 Z" fill="${teal}" stroke-width="4.5"/>
          <path d="M185 337 L238 337" stroke="#94B7A8" stroke-width="3" stroke-dasharray="4 5"/>
          <path d="M198 347 L205 353 L218 342" fill="none" stroke="${paper}" stroke-width="4"/>
        </g>

        <g class="char-head" style="transform-box:view-box;transform-origin:211px 234px" stroke="${ink}" stroke-linecap="round" stroke-linejoin="round">
          <g class="char-antenna">
            <path d="M211 95 L211 60 L222 48" fill="none" stroke-width="8"/>
            <circle cx="227" cy="43" r="15" fill="${amber}" stroke-width="6"/>
            <circle cx="224" cy="38" r="4" fill="#FFF0C5" stroke="none"/>
          </g>
          <rect x="82" y="147" width="36" height="51" rx="14" fill="${amber}" stroke-width="6"/>
          <rect x="306" y="147" width="36" height="51" rx="14" fill="${amber}" stroke-width="6"/>
          <path d="M92 160 L92 184 M332 160 L332 184" fill="none" stroke-width="4"/>
          <path d="M154 93 L269 93 Q320 93 324 143 L325 195 Q324 246 273 250 L151 250 Q101 247 100 199 L99 147 Q100 97 154 93 Z" fill="${teal}" stroke-width="8"/>
          <path d="M304 111 Q318 125 318 150 L319 193 Q319 239 273 243 L151 243 Q119 241 110 215 Q127 231 152 231 L269 231 Q306 230 307 192 L308 153 Q308 128 300 115" fill="#125B52" stroke="none"/>
          <path d="M116 139 Q122 109 151 108 L176 108" fill="none" stroke="#6EA799" stroke-width="5.5"/>
          <rect x="120" y="117" width="184" height="112" rx="37" fill="${paper}" stroke-width="5"/>
          <path d="M125 198 Q139 216 162 216 L265 216 Q286 216 299 203 Q294 224 273 224 L151 224 Q129 222 125 203 Z" fill="#E9E0D0" stroke="none"/>
          <g class="char-brows" fill="none" stroke-width="5">
            <path d="M152 141 Q165 131 181 137"/>
            <path d="M241 136 Q257 130 270 140"/>
          </g>
          <g class="char-eyes" ${faceRig}>
            <g class="char-eye-left" ${faceRig}>
              <ellipse cx="171" cy="162" rx="20" ry="23" fill="#FFFDF7" stroke-width="3.5"/>
              <ellipse cx="164" cy="164" rx="10" ry="14" fill="${ink}" stroke="none"/>
              <circle cx="162" cy="158" r="3.5" fill="#FFFDF7" stroke="none"/>
            </g>
            <g class="char-eye-right" ${faceRig}>
              <ellipse cx="253" cy="163" rx="20" ry="23" fill="#FFFDF7" stroke-width="3.5"/>
              <ellipse cx="246" cy="165" rx="10" ry="14" fill="${ink}" stroke="none"/>
              <circle cx="244" cy="159" r="3.5" fill="#FFFDF7" stroke="none"/>
            </g>
          </g>
          <path d="M208 169 Q214 165 218 170 L218 181 L205 181" fill="#94B7A8" stroke-width="3.5"/>
          <ellipse cx="145" cy="191" rx="10" ry="5.5" fill="#F1B7A1" stroke="none"/>
          <ellipse cx="280" cy="191" rx="10" ry="5.5" fill="#F1B7A1" stroke="none"/>
          <g class="char-mouth-open" ${faceRig}>
            <path d="M186 195 Q212 191 238 195 Q234 217 212 218 Q191 217 186 195 Z" fill="${ink}" stroke-width="3.5"/>
            <path d="M193 196 Q212 194 231 196 L228 202 L196 202 Z" fill="#FFFDF7" stroke="none"/>
            <path d="M204 213 Q215 205 226 211 Q218 216 212 215 Z" fill="${coral}" stroke="none"/>
          </g>
          <g class="char-mouth-closed" ${faceRig} opacity="0">
            <path d="M190 200 Q212 218 236 199" fill="none" stroke-width="4.5"/>
          </g>
          <path d="M134 103 L141 102 M281 102 L288 103" fill="none" stroke="${amber}" stroke-width="4"/>
        </g>
      </g>`;
  }

  function render(kind, prefix) {
    if (kind !== "nezha" && kind !== "patch") {
      throw new TypeError("Character kind must be 'nezha' or 'patch'.");
    }
    if (typeof prefix !== "string" || !/^[A-Za-z][A-Za-z0-9_-]*$/.test(prefix)) {
      throw new TypeError("Character prefix must be a unique, safe SVG identifier.");
    }
    const title = kind === "nezha"
      ? "Nezha, a curious orange phone in sneakers"
      : "Patch, a friendly teal robot engineer";
    const drawing = kind === "nezha" ? nezha(prefix) : patch(prefix);
    return `<svg id="${prefix}-character" class="twrp-character twrp-character--${kind}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 500" role="img" aria-labelledby="${prefix}-title" overflow="visible">
      <title id="${prefix}-title">${title}</title>${drawing}
    </svg>`;
  }

  global.TWRPCharacters = Object.freeze({ render });
})(window);
